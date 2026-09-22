import asyncio
import os

os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
os.environ["GOOGLE_CLOUD_PROJECT"] = "qwiklabs-gcp-01-426fafba1fca"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-east1"

import google.auth
from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions import VertexAiSessionService
from google.adk.memory import VertexAiMemoryBankService
from app.agent import app as adk_app

PROJECT_ID = "qwiklabs-gcp-01-426fafba1fca"
LOCATION = "us-east1"
ENGINE_ID = "677837923407626240"
USER_ID = "athlete_allergy_test_99"

async def test_memory_allergy_flow():
    session_service = VertexAiSessionService(
        project=PROJECT_ID, location=LOCATION, agent_engine_id=ENGINE_ID
    )
    memory_service = VertexAiMemoryBankService(
        project=PROJECT_ID, location=LOCATION, agent_engine_id=ENGINE_ID
    )
    runner = Runner(
        app=adk_app,
        session_service=session_service,
        memory_service=memory_service,
        auto_create_session=True,
    )

    print("--- Session 1: Storing Allergy Information ---")
    s1 = await runner.session_service.create_session(
        app_name=adk_app.name, user_id=USER_ID
    )
    msg1 = types.Content(
        role="user",
        parts=[types.Part.from_text(text="Hi FitCoach! Please remember that I am severely allergic to peanuts, tree nuts, and shellfish.")]
    )
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=s1.id,
        new_message=msg1,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "text", None):
                    print(part.text, end="")
    print("\n")

    print("Waiting 10 seconds for Memory Bank background extraction...")
    await asyncio.sleep(10)

    print("--- Session 2: Recalling Allergies in NEW Session ---")
    s2 = await runner.session_service.create_session(
        app_name=adk_app.name, user_id=USER_ID
    )
    msg2 = types.Content(
        role="user",
        parts=[types.Part.from_text(text="Can you list all my known allergies and recommend a safe post-workout snack?")]
    )
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=s2.id,
        new_message=msg2,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "text", None):
                    print(part.text, end="")
    print("\n")

if __name__ == "__main__":
    asyncio.run(test_memory_allergy_flow())
