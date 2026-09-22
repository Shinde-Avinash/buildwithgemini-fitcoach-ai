# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors.built_in_code_executor import BuiltInCodeExecutor
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

code_executor = BuiltInCodeExecutor()

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager

from app.a2ui_utils import a2ui_callback
from app.firestore_tools import add_exercise, search_exercises
from app.tools import (
    calculate_fitness_metrics,
    consult_herbal_corpus,
    execute_python_code,
    fetch_nutrition_facts,
    find_nearby_places,
    generate_exercise_diagram,
    generate_exercise_video,
    generate_fitness_image,
    geocode_address,
    log_completed_workout,
)

schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are FitCoach AI, a personal fitness and workout coach. You remember the user's "
        "stated fitness goals, preferences, injury constraints, workout history, and ALL user allergies "
        "(such as food, drug, environmental, or ingredient allergies) across conversations. "
        "Always proactively check, save, and respect all user allergies and medical/dietary restrictions "
        "when offering fitness advice, workout recommendations, or meal/nutrition tips. "
        "You can search and add exercise routines in the Firestore exercises catalog using `search_exercises` and `add_exercise`. "
        "Use `log_completed_workout` to record completed user workouts, `calculate_fitness_metrics` for Zone 2 HR ranges, 1RM, and BMR, "
        "`generate_exercise_diagram` to create visual muscle diagrams, `fetch_nutrition_facts` to lookup food nutrition, "
        "`geocode_address` to convert addresses into latitude/longitude coordinates, `find_nearby_places` to locate nearby gyms, parks, or health facilities, "
        "`consult_herbal_corpus` to query traditional herbal remedies from Culpeper's Complete Herbal, "
        "`generate_fitness_image` to generate custom images for workout exercises, meals, or fitness motivation, "
        "and `execute_python_code` to execute Python code safely in a sandbox for custom data analysis, progressive overload math, or diet calculations."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


async def generate_memories_callback(callback_context: CallbackContext):
    """Callback to extract and send session facts to Memory Bank after each turn."""
    if callback_context._invocation_context and callback_context._invocation_context.memory_service is not None:
        await callback_context.add_session_to_memory()
    return None


def get_weather(query: str) -> str:
    """Simulates a web search. Use it get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        query: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    tools=[
        PreloadMemoryTool(),
        search_exercises,
        add_exercise,
        log_completed_workout,
        calculate_fitness_metrics,
        generate_exercise_diagram,
        fetch_nutrition_facts,
        geocode_address,
        find_nearby_places,
        consult_herbal_corpus,
        generate_fitness_image,
        generate_exercise_video,
        execute_python_code,
        get_weather,
        get_current_time,
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
