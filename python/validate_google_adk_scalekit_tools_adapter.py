"""
validate_google_adk_scalekit_tools_adapter.py
-----------------------------
Verifies the Google ADK adapter section (step 7) in scalekit-optimized-tools.mdx.

Uses actions.google.get_tools to get native Google ADK tool objects and
invokes an Agent using the LiteLlm wrapper (no Gemini key needed — routes
through the LiteLLM proxy).

Run (from repo root):
    python python/validate_google_adk_scalekit_tools_adapter.py

Required env vars (.env at repo root):
    SCALEKIT_ENVIRONMENT_URL  SCALEKIT_CLIENT_ID  SCALEKIT_CLIENT_SECRET
    LITELLM_BASE_URL          LITELLM_API_KEY

Required packages:
    pip install google-adk litellm
"""

import os
import asyncio
import litellm
import scalekit.client
from dotenv import load_dotenv, find_dotenv
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

load_dotenv(find_dotenv())

print("=" * 60)
print("Step 7 Google ADK adapter verification")
print("=" * 60)

# Route through LiteLLM proxy — configure global litellm settings
litellm.api_base = os.getenv("LITELLM_BASE_URL")
litellm.api_key  = os.getenv("LITELLM_API_KEY")

# Initialize Scalekit client
scalekit_client = scalekit.client.ScalekitClient(
    env_url=os.getenv("SCALEKIT_ENVIRONMENT_URL"),
    client_id=os.getenv("SCALEKIT_CLIENT_ID"),
    client_secret=os.getenv("SCALEKIT_CLIENT_SECRET"),
)
actions = scalekit_client.actions

IDENTIFIER = "user_123"
MODEL_NAME = os.getenv("LITELLM_MODEL", "claude-sonnet-4-6")

# Fetch native Google ADK tool objects scoped to this user's Gmail
gmail_tools = actions.google.get_tools(
    identifier=IDENTIFIER,
    connection_names=["gmail"],
    page_size=100,
)

if not gmail_tools:
    print("  ❌ No tools returned from actions.google.get_tools — cannot continue")
    exit(1)

print(f"  ✅ actions.google.get_tools returned {len(gmail_tools)} tools: "
      f"{[t.name for t in gmail_tools[:5]]}")

# Build agent using LiteLlm wrapper (routes to LiteLLM proxy)
gmail_agent = Agent(
    name="validate_gmail_agent",
    model=LiteLlm(model=MODEL_NAME),
    description="Gmail assistant for verification",
    instruction="You are a helpful Gmail assistant. Use the available tools to answer questions about emails.",
    tools=gmail_tools,
)

# ADK uses Runner + session service for execution
async def run_agent(prompt: str) -> str:
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="validate_google_adk_scalekit_tools_adapter",
        user_id=IDENTIFIER,
        session_id="validate_session_001",
    )
    runner = Runner(
        agent=gmail_agent,
        app_name="validate_google_adk_scalekit_tools_adapter",
        session_service=session_service,
    )
    content = types.Content(
        role="user",
        parts=[types.Part(text=prompt)],
    )
    final_text = ""
    async for event in runner.run_async(
        user_id=IDENTIFIER,
        session_id=session.id,
        new_message=content,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text
    return final_text

response_text = asyncio.run(run_agent("list my 3 most recent emails"))

if response_text:
    print(f"\n  ✅ Agent responded ({len(response_text)} chars)")
    print(f"     Output (first 300 chars): {response_text[:300]}")
else:
    print("  ❌ Agent returned empty response")
