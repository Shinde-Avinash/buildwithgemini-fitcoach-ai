"""Firestore database tools for FitCoach AI exercises catalog.

Project ID is hardcoded as required for Agent Platform deployment compatibility.
"""

from typing import Optional
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-01-426fafba1fca"

# Initialize Firestore client with hardcoded project ID
db = firestore.Client(project=PROJECT_ID)
EXERCISES_COLLECTION = "exercises"


def search_exercises(category: str = "", target_muscle: str = "") -> str:
    """Search for exercise routines in the Firestore exercise database.

    Args:
        category: Optional category filter (e.g., 'Strength', 'Cardio', 'Flexibility', 'Bodyweight').
        target_muscle: Optional target muscle group filter (e.g., 'Legs', 'Chest', 'Back', 'Core', 'Full Body').

    Returns:
        A formatted list of matching exercise routines with details.
    """
    collection_ref = db.collection(EXERCISES_COLLECTION)
    query_ref = collection_ref

    if category:
        query_ref = query_ref.where("category", "==", category)
    if target_muscle:
        query_ref = query_ref.where("target_muscle", "==", target_muscle)

    docs = query_ref.stream()
    results = []
    for doc in docs:
        data = doc.to_dict()
        results.append(
            f"• {data.get('name', doc.id)} [{data.get('category', 'N/A')}] - "
            f"Target: {data.get('target_muscle', 'N/A')}, Difficulty: {data.get('difficulty', 'N/A')}\n"
            f"  Description: {data.get('description', 'No details available.')}"
        )

    if not results:
        return f"No exercises found matching category='{category}' and target_muscle='{target_muscle}'."

    return "Found Exercises:\n\n" + "\n\n".join(results)


def add_exercise(
    name: str,
    category: str,
    target_muscle: str,
    difficulty: str,
    description: str,
) -> str:
    """Add a new exercise routine to the Firestore exercise database.

    Args:
        name: Name of the exercise routine (e.g., 'Barbell Back Squat').
        category: Exercise category (e.g., 'Strength', 'Cardio', 'Bodyweight').
        target_muscle: Primary target muscle group (e.g., 'Legs', 'Chest', 'Core', 'Full Body').
        difficulty: Difficulty level ('Beginner', 'Intermediate', 'Advanced').
        description: Instructions or workout guidelines for performing the exercise.

    Returns:
        Confirmation message with document ID.
    """
    doc_ref = db.collection(EXERCISES_COLLECTION).document()
    doc_data = {
        "name": name,
        "category": category,
        "target_muscle": target_muscle,
        "difficulty": difficulty,
        "description": description,
    }
    doc_ref.set(doc_data)
    return f"Successfully added exercise '{name}' to Firestore database with Document ID: {doc_ref.id}"
