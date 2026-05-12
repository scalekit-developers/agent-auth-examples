"""
LangChain agent with Scalekit tools + LangSmith tracing.

Demonstrates that Scalekit's native LangChain StructuredTool objects trace
automatically in LangSmith when LANGCHAIN_TRACING_V2=true.

Run: python python/frameworks/langchain/langsmith_tracing.py

Required env vars (.env at repo root):
    SCALEKIT_ENVIRONMENT_URL  SCALEKIT_CLIENT_ID  SCALEKIT_CLIENT_SECRET
    LITELLM_BASE_URL          LITELLM_API_KEY
    LANGCHAIN_TRACING_V2=true
    LANGCHAIN_API_KEY          (this is the LangSmith API key)

Optional:
    LITELLM_MODEL      (default: "claude-sonnet-4-6")
    LANGCHAIN_PROJECT  (default: "scalekit-langsmith-test")
"""

import os

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

# ── Verify LangSmith tracing is configured ──────────────────────────────────

tracing_enabled = os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true"
langsmith_key = os.getenv("LANGCHAIN_API_KEY", "")
project = os.getenv("LANGCHAIN_PROJECT", "scalekit-langsmith-test")

if not tracing_enabled:
    print("⚠️  LANGCHAIN_TRACING_V2 is not set to 'true'. Traces will NOT be sent to LangSmith.")
    print("   Set LANGCHAIN_TRACING_V2=true in your .env to enable tracing.")
if not langsmith_key:
    print("⚠️  LANGCHAIN_API_KEY is not set. Traces will NOT be sent to LangSmith.")
    print("   Get your API key from https://smith.langchain.com/settings")
else:
    print(f"✅ LangSmith tracing enabled — project: {project}")

# ── Initialize Scalekit client ──────────────────────────────────────────────

import scalekit.client

scalekit_client = scalekit.client.ScalekitClient(
    client_id=os.getenv("SCALEKIT_CLIENT_ID"),
    client_secret=os.getenv("SCALEKIT_CLIENT_SECRET"),
    env_url=os.getenv("SCALEKIT_ENVIRONMENT_URL"),
)
actions = scalekit_client.actions

# ── Connect user to Gmail ───────────────────────────────────────────────────

IDENTIFIER = "user_123"

response = actions.get_or_create_connected_account(
    connection_name="gmail",
    identifier=IDENTIFIER,
)
if response.connected_account.status != "ACTIVE":
    link = actions.get_authorization_link(connection_name="gmail", identifier=IDENTIFIER)
    print("Authorize Gmail:", link.link)
    input("Press Enter after authorizing...")
else:
    print(f"✅ Gmail connected for {IDENTIFIER}")

# ── Get native LangChain tools ──────────────────────────────────────────────

tools = actions.langchain.get_tools(
    identifier=IDENTIFIER,
    connection_names=["gmail"],
)
tool_map = {t.name: t for t in tools}
print(f"✅ Loaded {len(tools)} LangChain tools: {[t.name for t in tools[:5]]}")

# ── Run agent with LangSmith tracing ────────────────────────────────────────

from langchain_core.messages import HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI

model = os.getenv("LITELLM_MODEL", "claude-sonnet-4-6")
llm = ChatOpenAI(
    model=model,
    openai_api_base=os.getenv("LITELLM_BASE_URL"),
    openai_api_key=os.getenv("LITELLM_API_KEY"),
).bind_tools(tools)
print(f"✅ Using model: {model} via LiteLLM")
messages = [HumanMessage("Fetch my last 3 unread emails and summarize them")]

print("\n--- Running agent (traces sent to LangSmith) ---\n")

tool_call_count = 0
while True:
    response = llm.invoke(messages)
    messages.append(response)
    if not response.tool_calls:
        print(response.content)
        break
    for tc in response.tool_calls:
        tool_call_count += 1
        print(f"  🔧 Tool call #{tool_call_count}: {tc['name']}")
        result = tool_map[tc["name"]].invoke(tc["args"])
        messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

# ── Summary ─────────────────────────────────────────────────────────────────

print(f"\n✅ Agent completed — {tool_call_count} tool call(s)")
if tracing_enabled and langsmith_key:
    print(f"✅ Check traces at: https://smith.langchain.com/o/default/projects/p/{project}")
    print("   (Open LangSmith → select your project → view the latest trace)")
