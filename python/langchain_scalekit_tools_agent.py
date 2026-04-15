"""
langchain_scalekit_tools_agent.py
----------------------------
Verifies the LangChain adapter section (step 7) in scalekit-optimized-tools.mdx.

Uses actions.langchain.get_tools to get native LangChain StructuredTool objects,
builds an OpenAI tools agent pointed at a LiteLLM proxy (no direct provider keys needed),
and invokes it with a read-only Gmail prompt.

Run (from repo root):
    python python/langchain_scalekit_tools_agent.py

Required env vars (.env at repo root):
    SCALEKIT_ENVIRONMENT_URL  SCALEKIT_CLIENT_ID  SCALEKIT_CLIENT_SECRET
    LITELLM_BASE_URL          LITELLM_API_KEY

Required packages:
    pip install langchain langchain-openai
"""

import os
import scalekit.client
from dotenv import load_dotenv, find_dotenv
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

load_dotenv(find_dotenv())

print("=" * 60)
print("Step 7 LangChain adapter verification")
print("=" * 60)

# Initialize Scalekit client
scalekit_client = scalekit.client.ScalekitClient(
    env_url=os.getenv("SCALEKIT_ENVIRONMENT_URL"),
    client_id=os.getenv("SCALEKIT_CLIENT_ID"),
    client_secret=os.getenv("SCALEKIT_CLIENT_SECRET"),
)
actions = scalekit_client.actions

IDENTIFIER = "user_123"
MODEL_NAME = os.getenv("LITELLM_MODEL", "claude-sonnet-4-6")

# Fetch native LangChain StructuredTool objects scoped to this user's Gmail
tools = actions.langchain.get_tools(
    identifier=IDENTIFIER,
    connection_names=["gmail"],
    page_size=100,
)

if not tools:
    print("  ❌ No tools returned from actions.langchain.get_tools — cannot continue")
    exit(1)

print(f"  ✅ actions.langchain.get_tools returned {len(tools)} tools: "
      f"{[t.name for t in tools[:5]]}")

# Point ChatOpenAI at LiteLLM (OpenAI-compat endpoint) — no OpenAI key needed
llm = ChatOpenAI(
    model=MODEL_NAME,
    openai_api_base=os.getenv("LITELLM_BASE_URL"),
    openai_api_key=os.getenv("LITELLM_API_KEY"),
)

agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt="You are a helpful assistant. Use tools if needed.",
)
result = agent.invoke({
    "messages": [{"role": "user", "content": "list my 3 most recent emails"}]
})

messages = result.get("messages", [])
output = ""
for msg in reversed(messages):
    if getattr(msg, "type", "") == "ai" and getattr(msg, "content", ""):
        output = msg.content
        break

tool_call_count = sum(1 for msg in messages if getattr(msg, "type", "") == "tool")
if output:
    print(f"\n  ✅ Agent responded ({len(output)} chars)")
    print(f"  ✅ Tool calls observed: {tool_call_count}")
    print(f"     Output (first 300 chars): {output[:300]}")
else:
    print("  ❌ Agent returned empty output")
