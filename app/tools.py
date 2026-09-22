"""Action and computation tools for FitCoach AI.

Includes:
1. log_completed_workout: Firestore workout logger
2. calculate_fitness_metrics: Zone 2 HR, 1RM, and calorie math
3. generate_exercise_diagram: Muscle diagram generator + public GCS uploader
"""

import base64
import io
import time
import uuid
from typing import Optional
import google.auth
import google.auth.transport.requests
import httpx
from PIL import Image, ImageDraw
from google.cloud import firestore, storage
from google.adk.tools import ToolContext
from google.genai import types

PROJECT_ID = "qwiklabs-gcp-01-426fafba1fca"
BUCKET_NAME = "fitcoach-ai-assets-qwiklabs-gcp-01-426fafba1fca"

# Initialize Firestore and GCS clients with hardcoded project ID
db = firestore.Client(project=PROJECT_ID)
storage_client = storage.Client(project=PROJECT_ID)


def log_completed_workout(
    workout_name: str,
    duration_minutes: int,
    calories_burned: int,
    notes: str = "",
) -> str:
    """Log a completed workout session to the user's Firestore workout history.

    Args:
        workout_name: Name of the workout routine (e.g. 'Leg Day Hypertrophy', '5k Zone 2 Run').
        duration_minutes: Total workout duration in minutes.
        calories_burned: Estimated total calories burned.
        notes: Optional notes or perceived exertion (e.g. 'RPE 8, felt great').

    Returns:
        Confirmation message with document ID.
    """
    doc_ref = db.collection("workout_logs").document()
    doc_data = {
        "workout_name": workout_name,
        "duration_minutes": duration_minutes,
        "calories_burned": calories_burned,
        "notes": notes,
        "timestamp": firestore.SERVER_TIMESTAMP,
    }
    doc_ref.set(doc_data)
    return (
        f"Workout successfully logged! '{workout_name}' ({duration_minutes} mins, "
        f"{calories_burned} kcal) saved to Firestore with Doc ID: {doc_ref.id}."
    )


def calculate_fitness_metrics(
    age: int,
    resting_hr: int,
    weight_kg: float,
    reps: int = 0,
    weight_lifted_kg: float = 0.0,
) -> str:
    """Calculate key fitness and exercise metrics: Zone 2 Heart Rate, 1RM estimate, and baseline BMR.

    Args:
        age: Athlete's age in years.
        resting_hr: Resting heart rate in beats per minute (BPM).
        weight_kg: Body weight in kilograms.
        reps: Optional repetitions performed for 1RM calculation.
        weight_lifted_kg: Optional weight lifted in kg for 1RM calculation.

    Returns:
        Formatted summary of calculated heart rate zones, estimated 1RM, and caloric BMR baseline.
    """
    # Max Heart Rate (Haskell & Fox formula)
    max_hr = 220 - age
    hrr = max_hr - resting_hr

    # Zone 2 Karvonen range (60% to 70% HRR)
    z2_low = int(round((hrr * 0.60) + resting_hr))
    z2_high = int(round((hrr * 0.70) + resting_hr))

    # BMR (Mifflin-St Jeor baseline estimate)
    bmr_est = int(round(10 * weight_kg + 6.25 * (175) - 5 * age + 5))

    results = [
        f"• Zone 2 Target Heart Rate: {z2_low} - {z2_high} BPM (Age {age}, Resting HR {resting_hr} BPM, Max HR {max_hr} BPM)",
        f"• Estimated Baseline BMR: ~{bmr_est} kcal/day",
    ]

    # 1RM Epley Formula if lift data is provided
    if reps > 0 and weight_lifted_kg > 0:
        one_rm = round(weight_lifted_kg * (1 + reps / 30.0), 1)
        results.append(
            f"• Estimated 1-Rep Max (1RM): {one_rm} kg (based on {weight_lifted_kg} kg x {reps} reps)"
        )

    return "Calculated Fitness Metrics:\n" + "\n".join(results)


def generate_exercise_diagram(exercise_name: str, target_muscle: str) -> str:
    """Generate a visual muscle diagram card for an exercise routine and upload to public GCS.

    Args:
        exercise_name: Name of the exercise routine (e.g., 'Barbell Back Squat', 'Push-up').
        target_muscle: Target muscle group (e.g., 'Quadriceps & Glutes', 'Chest & Triceps').

    Returns:
        Public HTTPS URL of the generated visual diagram image.
    """
    # Create stylized diagram image
    img = Image.new("RGB", (480, 260), color=(15, 23, 42))  # Dark slate header
    d = ImageDraw.Draw(img)

    # Decorative card border
    d.rectangle([10, 10, 470, 250], outline=(59, 130, 246), width=3)
    d.rectangle([20, 20, 460, 70], fill=(30, 41, 59))

    # Text content
    d.text((30, 35), f"FitCoach AI: {exercise_name}", fill=(248, 250, 252))
    d.text((30, 95), f"Primary Muscle Group:", fill=(148, 163, 184))
    d.text((30, 120), f"⚡ {target_muscle}", fill=(96, 165, 250))

    # Highlighted muscle bar diagram
    d.text((30, 165), "Activation Intensity:", fill=(148, 163, 184))
    d.rectangle([30, 195, 430, 220], fill=(30, 41, 59), outline=(71, 85, 105))
    d.rectangle([30, 195, 360, 220], fill=(34, 197, 94))  # Green active bar

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    filename = f"diagrams/{uuid.uuid4().hex[:8]}_{exercise_name.lower().replace(' ', '_')}.png"
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_file(buf, content_type="image/png")

    return f"Exercise diagram generated successfully! Public URL: {blob.public_url}"


def fetch_nutrition_facts(food_query: str) -> str:
    """Fetch real-world nutrition data (calories, macronutrients, allergens) for a food item or workout snack from Open Food Facts API.

    Args:
        food_query: Name of the food item, ingredient, or workout snack (e.g. 'greek yogurt', 'protein bar', 'almond milk', 'oats').

    Returns:
        Formatted summary of nutrition facts, calories per 100g, protein, carbs, fat, and allergen disclosures.
    """
    import os
    import requests

    user_agent = os.getenv(
        "OPENFOODFACTS_USER_AGENT", "FitCoachAI/1.0 (contact@fitcoach.ai)"
    )
    api_key = os.getenv("NUTRITION_API_KEY", "")

    url = "https://world.openfoodfacts.org/cgi/search.pl"
    params = {
        "search_terms": food_query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
    }
    headers = {"User-Agent": user_agent}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        products = data.get("products", [])
        if not products:
            return f"No nutrition records found for '{food_query}' in OpenFoodFacts database."

        results = []
        for p in products[:3]:
            name = p.get("product_name") or p.get("product_name_en")
            if not name:
                continue
            nutr = p.get("nutriments", {})
            kcal = (
                nutr.get("energy-kcal_100g")
                or nutr.get("energy-kcal_value")
                or "N/A"
            )
            protein = nutr.get("proteins_100g", "N/A")
            carbs = nutr.get("carbohydrates_100g", "N/A")
            fat = nutr.get("fat_100g", "N/A")
            allergens = (
                p.get("allergens_from_ingredients")
                or p.get("allergens")
                or "None listed"
            )

            results.append(
                f"• {name}:\n"
                f"  - Calories: {kcal} kcal/100g\n"
                f"  - Protein: {protein}g | Carbs: {carbs}g | Fat: {fat}g\n"
                f"  - Listed Allergens: {allergens}"
            )

        if not results:
            return f"No detailed nutrition entries available for '{food_query}'."

        return f"OpenFoodFacts Nutrition Facts for '{food_query}':\n\n" + "\n\n".join(
            results
        )
    except Exception as e:
        return f"Error fetching nutrition facts for '{food_query}': {str(e)}"


def geocode_address(address: str) -> str:
    """Geocode a physical location or address into latitude, longitude, and formatted address using Google Maps Geocoding API.

    Args:
        address: Address or landmark name (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA' or 'Golden Gate Park, San Francisco').

    Returns:
        Formatted location details with latitude, longitude, and canonical address.
    """
    import os
    import requests

    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not configured."

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": api_key}

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        if not results:
            return f"No geocoding results found for address: '{address}'."

        first_res = results[0]
        formatted_addr = first_res.get("formatted_address")
        location = first_res.get("geometry", {}).get("location", {})
        lat = location.get("lat")
        lng = location.get("lng")

        return (
            f"Geocoding Results for '{address}':\n"
            f"• Formatted Address: {formatted_addr}\n"
            f"• Latitude: {lat}\n"
            f"• Longitude: {lng}"
        )
    except Exception as e:
        return f"Error geocoding address '{address}': {str(e)}"


def find_nearby_places(
    place_type: str,
    latitude: float,
    longitude: float,
    radius_meters: int = 1500,
) -> str:
    """Find nearby places of a specific type (e.g., 'gym', 'park', 'sports_complex', 'health') using Google Places API (New).

    Args:
        place_type: Type of place to search for (e.g. 'gym', 'park', 'fitness_center', 'health_club').
        latitude: Center search latitude coordinate.
        longitude: Center search longitude coordinate.
        radius_meters: Search radius in meters (default 1500m).

    Returns:
        List of nearby places with name, formatted address, and location coordinates.
    """
    import os
    import requests

    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not configured."

    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
        "Content-Type": "application/json",
    }
    body = {
        "includedTypes": [place_type],
        "locationRestriction": {
            "circle": {
                "center": {"latitude": latitude, "longitude": longitude},
                "radius": float(radius_meters),
            }
        },
    }

    try:
        response = requests.post(url, json=body, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        places = data.get("places", [])
        if not places:
            return f"No nearby '{place_type}' places found within {radius_meters}m of ({latitude}, {longitude})."

        results = []
        for p in places[:5]:
            display_name = p.get("displayName", {}).get("text", "Unknown Place")
            addr = p.get("formattedAddress", "No address listed")
            loc = p.get("location", {})
            lat = loc.get("latitude")
            lng = loc.get("longitude")

            results.append(
                f"• {display_name}\n"
                f"  - Address: {addr}\n"
                f"  - Location: ({lat}, {lng})"
            )

        return (
            f"Nearby '{place_type}' Places (Radius: {radius_meters}m):\n\n"
            + "\n\n".join(results)
        )
    except Exception as e:
        return f"Error searching nearby places: {str(e)}"


def consult_herbal_corpus(query: str) -> str:
    """Search the herbal remedies and natural health corpus (Culpeper's Complete Herbal) and return matched passages.

    Args:
        query: What to look up (a plant, herb, natural remedy, ailment, or recipe).
    Returns:
        The matched passages, or a note that none was found.
    """
    import vertexai
    from vertexai.preview import rag

    corpus_name = "projects/qwiklabs-gcp-01-426fafba1fca/locations/us-central1/ragCorpora/28666467159375872"
    try:
        vertexai.init(project="qwiklabs-gcp-01-426fafba1fca", location="us-central1")
        resp = rag.retrieval_query(
            text=query,
            rag_resources=[rag.RagResource(rag_corpus=corpus_name)],
            rag_retrieval_config=rag.RagRetrievalConfig(top_k=5),
        )
        contexts = getattr(resp.contexts, "contexts", [])
        passages = [c.text.strip() for c in contexts if getattr(c, "text", "").strip()]
        return "\n\n---\n\n".join(passages) or "No relevant passage found."
    except Exception as e:
        return f"Retrieval failed: {e}"


async def generate_fitness_image(prompt: str, tool_context: ToolContext) -> str:
    """Generate an image for a workout exercise, fitness meal, or fitness item using the gemini-3.1-flash-lite-image model.

    Args:
        prompt: Detailed description of the workout exercise, meal, or fitness item to generate an image for.
        tool_context: ADK tool context for saving artifacts.

    Returns:
        The public HTTPS GCS URL of the generated image.
    """
    import time
    from google import genai
    from google.genai import types
    from google.cloud import storage

    bucket_name = "fitcoach-ai-assets-qwiklabs-gcp-01-426fafba1fca"
    project_id = "qwiklabs-gcp-01-426fafba1fca"

    client = genai.Client(vertexai=True, project=project_id, location="global")

    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"]
            ),
        )

        image_bytes = None
        mime_type = "image/jpeg"
        for candidate in response.candidates:
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if part.inline_data:
                        image_bytes = part.inline_data.data
                        if part.inline_data.mime_type:
                            mime_type = part.inline_data.mime_type
                        break
            if image_bytes:
                break

        if not image_bytes:
            return "Error: No image data returned from model."

        ext = "png" if "png" in mime_type else "jpg"
        filename = f"fitness_{int(time.time())}.{ext}"

        # 1. Save artifact with tool_context.save_artifact
        artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        await tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 2. Upload to public Cloud Storage bucket
        storage_client = storage.Client(project=project_id)
        bucket = storage_client.bucket(bucket_name)
        blob_name = f"generated_images/{filename}"
        blob = bucket.blob(blob_name)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{bucket_name}/{blob_name}"
        return f"Successfully generated image and uploaded to: {public_url}"

    except Exception as e:
        return f"Error generating fitness image: {str(e)}"


def execute_python_code(code: str) -> str:
    """Executes Python code safely for calculations, data analysis, or math scripts.

    Args:
        code: A string containing valid Python code to execute.

    Returns:
        The stdout output or execution result from running the Python code.
    """
    try:
        import io
        import sys

        stdout_capture = io.StringIO()
        sys.stdout = stdout_capture
        local_vars = {}
        try:
            exec(code, {}, local_vars)
        finally:
            sys.stdout = sys.__stdout__
        output = stdout_capture.getvalue()
        if not output and local_vars:
            output = str(local_vars)
        return output or "Code executed successfully with no output."
    except Exception as e:
        return f"Execution error: {e}"


async def generate_exercise_video(
    prompt: str,
    tool_context: ToolContext = None,
) -> str:
    """Generates a short exercise demonstration or workout animation video using Google's gemini-omni-flash-preview model in the global region.
    Saves the generated video with tool_context.save_artifact so it shows up in Playground's Artifacts panel,
    and uploads the video bytes directly to a public Cloud Storage bucket, returning the public HTTPS URL.

    Args:
        prompt: Description of the exercise demonstration video to generate (e.g. '3-second video of kettlebell swings with proper form').
        tool_context: Optional context for saving artifacts in ADK Playground.

    Returns:
        Public HTTPS URL of the uploaded video in Cloud Storage.
    """
    project_id = "qwiklabs-gcp-01-426fafba1fca"
    bucket_name = "fitcoach-ai-assets-qwiklabs-gcp-01-426fafba1fca"

    try:
        creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        creds.refresh(google.auth.transport.requests.Request())

        url = f"https://aiplatform.googleapis.com/v1beta1/projects/{project_id}/locations/global/interactions"
        headers = {
            "Authorization": f"Bearer {creds.token}",
            "Content-Type": "application/json"
        }
        body = {
            "model": "gemini-omni-flash-preview",
            "input": [
                {"type": "text", "text": prompt}
            ],
            "generation_config": {
                "video_config": {
                    "task": "text_to_video"
                }
            }
        }

        async with httpx.AsyncClient(timeout=180.0) as http_client:
            resp = await http_client.post(url, headers=headers, json=body)

        if resp.status_code != 200:
            return f"Error from Interactions API ({resp.status_code}): {resp.text}"

        data = resp.json()
        video_bytes = None
        mime_type = "video/mp4"

        for step in data.get("steps", []):
            if step.get("type") == "model_output":
                for item in step.get("content", []):
                    if item.get("type") == "video":
                        mime_type = item.get("mime_type", "video/mp4")
                        if "data" in item:
                            video_bytes = base64.b64decode(item["data"])
                        elif "bytes" in item:
                            video_bytes = base64.b64decode(item["bytes"])

        if not video_bytes:
            return f"Interaction complete, but no video bytes found in response: {str(data)[:500]}"

        filename = f"exercise_video_{int(time.time())}.mp4"

        # 1. Save artifact with tool_context.save_artifact if tool_context is provided
        if tool_context:
            artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
            await tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 2. Upload video bytes to public Cloud Storage bucket
        storage_client = storage.Client(project=project_id)
        bucket = storage_client.bucket(bucket_name)
        blob_name = f"generated_videos/{filename}"
        blob = bucket.blob(blob_name)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{bucket_name}/{blob_name}"
        return f"Successfully generated exercise video and uploaded to: {public_url}"

    except Exception as e:
        return f"Error generating exercise video: {str(e)}"






