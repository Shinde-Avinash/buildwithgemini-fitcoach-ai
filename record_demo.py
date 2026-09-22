import asyncio
import os
import shutil
import time
from playwright.async_api import async_playwright
from google.cloud import storage

PROJECT_ID = "qwiklabs-gcp-01-426fafba1fca"
BUCKET_NAME = "fitcoach-ai-assets-qwiklabs-gcp-01-426fafba1fca"

async def record_demo():
    print("Starting Playwright demo recording...")
    output_dir = os.path.abspath("demo_video_raw")
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path="/usr/bin/google-chrome",
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(
            record_video_dir=output_dir,
            record_video_size={"width": 1280, "height": 800},
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        print("Navigating to http://localhost:8080...")
        await page.goto("http://localhost:8080")
        await asyncio.sleep(3)

        # 1. First interaction: Click prompt chip '30-min HIIT Workout Card'
        print("Executing Action 1: Clicking HIIT Workout Chip...")
        chips = await page.query_selector_all(".prompt-chip")
        if chips:
            await chips[0].click()
            print("Clicked chip 0 successfully")
        else:
            await page.fill("#input", "Design a 30-min HIIT kettlebell workout & show summary card")
            await page.click("#form button[type='submit']")

        # Wait for agent response to stream in and render A2UI card
        print("Waiting for response to first prompt...")
        await asyncio.sleep(12)
        await page.evaluate("window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'})")
        await asyncio.sleep(4)

        # 2. Second interaction: Rich prompt showing tool calls (DB search, Zone 2 HR math, image generation)
        rich_prompt = "Search Firestore for strength exercises, calculate my Zone 2 target HR for resting HR 60 and age 28, and generate a motivational fitness image of an athlete at sunrise."
        print(f"Executing Action 2: Filling input with rich prompt: '{rich_prompt}'...")

        await page.fill("#input", rich_prompt)
        await asyncio.sleep(1)
        await page.click("#form button[type='submit']")

        print("Waiting for response to rich prompt (tool calls, DB lookup & image generation)...")
        # Tool execution + image generation takes ~18 seconds
        await asyncio.sleep(22)

        # Scroll down smoothly to show complete results and generated image
        await page.evaluate("window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'})")
        await asyncio.sleep(6)

        # Close context to flush video recording to disk
        await page.close()
        await context.close()
        await browser.close()

    # Find the recorded video file
    video_files = [f for f in os.listdir(output_dir) if f.endswith(".webm")]
    if not video_files:
        print("Error: No video file found!")
        return None

    raw_video_path = os.path.join(output_dir, video_files[0])
    target_video_path = os.path.abspath("fitcoach_ai_demo.webm")
    shutil.copyfile(raw_video_path, target_video_path)
    file_size_mb = os.path.getsize(target_video_path) / (1024 * 1024)
    print(f"Demo video saved locally to {target_video_path} (size: {file_size_mb:.2f} MB)")

    # Upload video to public Cloud Storage bucket
    print("Uploading demo video to GCS bucket fitcoach-ai-assets-qwiklabs-gcp-01-426fafba1fca...")
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob_name = f"demo/fitcoach_ai_demo_{int(time.time())}.webm"
    blob = bucket.blob(blob_name)
    with open(target_video_path, "rb") as f:
        blob.upload_from_file(f, content_type="video/webm")

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"
    print(f"Public video URL: {public_url}")
    return public_url

if __name__ == "__main__":
    asyncio.run(record_demo())
