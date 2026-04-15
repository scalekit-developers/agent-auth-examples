"""
verify_optimized_tools.py
---------------------------
Verifies the code snippets in scalekit-optimized-tools.mdx, steps 1–6.

Checkpoints:
  ✅ Step 2: SDK initializes from env vars
  ✅ Step 3: list_tools returns results; list_scoped_tools returns per-user tools with input_schema
  ✅ Step 4: get_or_create_connected_account + get_connected_account work
  ✅ Step 1 (negative): executing a tool for an unknown user raises ScalekitNotFoundException
  ✅ Step 5: execute_tool runs a read-only tool per connector (gmail, github, linear)
  ✅ Step 6: Anthropic LLM loop via LiteLLM proxy completes with at least one tool_use

Run (from repo root):
    python python/verify_optimized_tools.py

Required env vars (.env at repo root):
    SCALEKIT_ENVIRONMENT_URL  SCALEKIT_CLIENT_ID  SCALEKIT_CLIENT_SECRET
    LITELLM_BASE_URL          LITELLM_API_KEY
"""

import os
import sys
import scalekit.client
import anthropic
from dotenv import load_dotenv, find_dotenv
from scalekit.common.exceptions import ScalekitNotFoundException
from google.protobuf.json_format import MessageToDict

load_dotenv(find_dotenv())

# ── Helpers ───────────────────────────────────────────────────────────────────

def ok(msg):     print(f"  ✅ {msg}")
def fail(msg):   print(f"  ❌ {msg}")
def warn(msg):   print(f"  ⚠️  {msg}")
def note(msg):   print(f"     {msg}")
def section(t):  print(f"\n{'─' * 60}\n{t}\n{'─' * 60}")

IDENTIFIER  = "user_123"
CONNECTOR_TARGETS = [
    ("gmail", os.getenv("GMAIL_CONNECTION_NAME", "gmail")),
    ("github", os.getenv("GITHUB_CONNECTION_NAME", "github-qkHFhMip")),
    ("linear", os.getenv("LINEAR_CONNECTION_NAME", "linear")),
]
READ_PREFIXES = ("list_", "fetch_", "get_", "search_", "read_")
MODEL_NAME = os.getenv("LITELLM_MODEL", "claude-sonnet-4-6")
INTERACTIVE = os.getenv("VERIFY_INTERACTIVE", "true").lower() == "true" and sys.stdin.isatty()

def _unpack_response(maybe_tuple):
    if isinstance(maybe_tuple, tuple):
        return maybe_tuple[0]
    return maybe_tuple

def _scoped_tool_to_dict(scoped_tool):
    return MessageToDict(scoped_tool)

def _tool_def_from_scoped_dict(scoped_tool_dict):
    return (scoped_tool_dict or {}).get("tool", {}).get("definition", {})

# ── STEP 2: Initialize SDK client ─────────────────────────────────────────────

section("Step 2 — Initialize SDK client")

scalekit_client = scalekit.client.ScalekitClient(
    env_url=os.getenv("SCALEKIT_ENVIRONMENT_URL"),
    client_id=os.getenv("SCALEKIT_CLIENT_ID"),
    client_secret=os.getenv("SCALEKIT_CLIENT_SECRET"),
)
actions = scalekit_client.actions

ok("SDK initialized — scalekit_client.actions ready")

# ── STEP 3: Discover tools ─────────────────────────────────────────────────────

section("Step 3 — Discover tools")

all_tools_resp = _unpack_response(actions.tools.list_tools())
tool_names = list(getattr(all_tools_resp, "tool_names", []))
ok(f"list_tools — {len(tool_names)} tools in workspace")

scoped_by_connector = {}
for label, conn_name in CONNECTOR_TARGETS:
    try:
        scoped = _unpack_response(actions.tools.list_scoped_tools(
            identifier=IDENTIFIER,
            filter={"connection_names": [conn_name]},
        ))
    except ScalekitNotFoundException as e:
        scoped_by_connector[label] = []
        warn(f"list_scoped_tools({label} -> {conn_name}) not found for identifier={IDENTIFIER}; continuing")
        note(f"Error: {e}")
        continue
    scoped_tools = list(getattr(scoped, "tools", []))
    scoped_by_connector[label] = [_scoped_tool_to_dict(t) for t in scoped_tools]
    names = [
        _tool_def_from_scoped_dict(t).get("name")
        for t in scoped_by_connector[label][:5]
        if _tool_def_from_scoped_dict(t).get("name")
    ]
    ok(f"list_scoped_tools({label} -> {conn_name}) — {len(scoped_tools)} tools: {names}")
    if scoped_by_connector[label]:
        first_def = _tool_def_from_scoped_dict(scoped_by_connector[label][0])
        schema = first_def.get("input_schema", {})
        if schema and "properties" in schema:
            ok(f"  input_schema for '{first_def.get('name', 'unknown')}': "
               f"properties={list(schema.get('properties', {}).keys())[:5]}")
        else:
            note(f"input_schema for '{first_def.get('name', 'unknown')}': {schema}")

# ── STEP 4: Authorize user ─────────────────────────────────────────────────────

section("Step 4 — Authorize user")

for label, conn_name in CONNECTOR_TARGETS:
    try:
        resp = actions.get_or_create_connected_account(
            connection_name=conn_name,
            identifier=IDENTIFIER,
        )
    except ScalekitNotFoundException as e:
        warn(f"{label} ({conn_name}): connection not found in workspace; skipping auth/execute for this connector")
        note(f"Error: {e}")
        scoped_by_connector[label] = []
        continue
    account = resp.connected_account
    status = account.status if account else "unknown"

    if status == "ACTIVE":
        ok(f"{label}: connected account ACTIVE (id={account.id})")
        details = actions.get_connected_account(
            connection_name=conn_name,
            identifier=IDENTIFIER,
        )
        ca = details.connected_account
        ok(f"  get_connected_account — token_expires_at={ca.token_expires_at}, "
           f"last_used_at={ca.last_used_at}")
    else:
        link = actions.get_authorization_link(
            connection_name=conn_name,
            identifier=IDENTIFIER,
        )
        print(f"\n  ⚠️  {label} not ACTIVE (status={status})")
        print(f"  Authorize here: {link.link}")
        if INTERACTIVE:
            input(f"  Press Enter after authorizing {label}…\n")
        else:
            warn("Non-interactive mode: skipping wait for manual authorization")
            continue
        # re-check
        resp2 = actions.get_or_create_connected_account(connection_name=conn_name, identifier=IDENTIFIER)
        a2 = resp2.connected_account
        if a2 and a2.status == "ACTIVE":
            ok(f"{label}: now ACTIVE")
        else:
            fail(f"{label}: still not ACTIVE (status={a2.status if a2 else 'unknown'}) — skipping execute")

# ── STEP 1 (negative): Missing connection raises resource not found ─────────────

section("Step 1 (negative) — Missing connection raises ScalekitNotFoundException")

known_tool_name = next(
    (
        _tool_def_from_scoped_dict(t).get("name")
        for conn_tools in scoped_by_connector.values()
        for t in conn_tools
        if _tool_def_from_scoped_dict(t).get("name")
    ),
    "gmail_fetch_mails",
)

try:
    actions.execute_tool(
        tool_name=known_tool_name,
        tool_input={"max_results": 1},
        identifier="__verify_nonexistent_user_xyz__",
    )
    fail("Expected ScalekitNotFoundException — got success instead")
except ScalekitNotFoundException as e:
    ok(f"ScalekitNotFoundException raised as expected")
    note(f"Error: {e}")
except Exception as e:
    message = str(e).lower()
    if "resource_not_found" in message or "not_found" in message:
        ok(f"Resource-not-found style error raised as expected ({type(e).__name__})")
        note(f"Error: {e}")
    else:
        warn(f"Got {type(e).__name__} (not ScalekitNotFoundException): {e}")
        note("The mdx claims 'resource not found' — actual exception type may differ")

# ── STEP 5: Execute tool per connector ────────────────────────────────────────

section("Step 5 — Execute tool across connectors")

for label, _conn_name in CONNECTOR_TARGETS:
    tools_for_conn = scoped_by_connector.get(label, [])
    if not tools_for_conn:
        warn(f"{label}: no scoped tools — skipping execute")
        continue

    # pick first read-only tool by name prefix; fall back to first available
    candidate = next((t for t in tools_for_conn if any(
        _tool_def_from_scoped_dict(t).get("name", "").startswith(p) for p in READ_PREFIXES
    )), tools_for_conn[0])
    candidate_def = _tool_def_from_scoped_dict(candidate)
    candidate_name = candidate_def.get("name", "")

    # build minimal required input from JSON Schema
    schema = candidate_def.get("input_schema") or {}
    required_fields = schema.get("required", [])
    props = schema.get("properties", {})
    tool_input = {}
    for field in required_fields:
        fdef = props.get(field, {})
        ftype = fdef.get("type", "string")
        if isinstance(ftype, list):
            ftype = next((t for t in ftype if t != "null"), "string")
        if ftype == "integer":   tool_input[field] = 1
        elif ftype == "boolean": tool_input[field] = False
        else:                    tool_input[field] = ""

    try:
        result = actions.execute_tool(
            tool_name=candidate_name,
            tool_input=tool_input,
            identifier=IDENTIFIER,
        )
        keys = list(result.data.keys()) if isinstance(result.data, dict) else type(result.data).__name__
        ok(f"{label}: execute_tool('{candidate_name}') → data keys: {keys}")
    except Exception as e:
        message = str(e).lower()
        if "not active" in message:
            warn(f"{label}: execute_tool('{candidate_name}') skipped because connected account is not ACTIVE")
        else:
            fail(f"{label}: execute_tool('{candidate_name}') raised {type(e).__name__}: {e}")

    # surface real tool names so we can compare against mdx table
    note(f"Actual {label} tool names: {[_tool_def_from_scoped_dict(t).get('name') for t in tools_for_conn[:5]]}")

# ── STEP 6: Full LLM tool-calling loop (Anthropic SDK → LiteLLM) ─────────────

section("Step 6 — Full LLM tool-calling loop")

litellm_url = os.getenv("LITELLM_BASE_URL")
litellm_key = os.getenv("LITELLM_API_KEY")

if not litellm_url or not litellm_key:
    warn("LITELLM_BASE_URL or LITELLM_API_KEY not set — skipping step 6")
else:
    try:
        # 1. Fetch scoped gmail tools for this user
        gmail_connection_name = next(
            (conn_name for label, conn_name in CONNECTOR_TARGETS if label == "gmail"),
            "gmail",
        )
        scoped = _unpack_response(actions.tools.list_scoped_tools(
            identifier=IDENTIFIER,
            filter={"connection_names": [gmail_connection_name]},
        ))
        scoped_tools = [_scoped_tool_to_dict(t) for t in getattr(scoped, "tools", [])]
        # Reshape to Anthropic tool format — matches mdx exactly
        llm_tools = [
            {
                "name": _tool_def_from_scoped_dict(t).get("name"),
                "description": _tool_def_from_scoped_dict(t).get("description"),
                "input_schema": _tool_def_from_scoped_dict(t).get("input_schema", {}),
            }
            for t in scoped_tools
            if _tool_def_from_scoped_dict(t).get("name")
        ]

        # 2. Send user message to the LLM with tools attached
        client = anthropic.Anthropic(base_url=litellm_url, api_key=litellm_key)
        messages = [{"role": "user", "content": "Summarize my last 5 unread emails"}]

        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=1024,
            tools=llm_tools,
            messages=messages,
        )

        # 3. Execute any tool_use blocks the LLM requested
        tool_use_count = 0
        for block in response.content:
            if block.type == "tool_use":
                tool_use_count += 1
                tool_result = actions.execute_tool(
                    tool_name=block.name,
                    tool_input=block.input,
                    identifier=IDENTIFIER,
                )
                # 4. Append result back for the final completion
                messages.append({"role": "assistant", "content": response.content})
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(tool_result.data),
                    }],
                })

        if tool_use_count > 0:
            final = client.messages.create(
                model=MODEL_NAME,
                max_tokens=1024,
                tools=llm_tools,
                messages=messages,
            )
            final_text = next(
                (b.text for b in final.content if hasattr(b, "text") and b.text), ""
            )
            if final_text:
                ok(f"LLM loop: {tool_use_count} tool_use(s) executed, final text received "
                   f"({len(final_text)} chars)")
                note(f"Final text (first 300 chars): {final_text[:300]}")
            else:
                warn("LLM loop: tool_use executed but no final text in response")
        else:
            warn(f"LLM loop: no tool_use blocks (stop_reason={response.stop_reason}) — "
                 f"LLM may not have called a tool")
            note(f"Content types: {[b.type for b in response.content]}")
    except Exception as e:
        msg = str(e).lower()
        if "budget has been exceeded" in msg or "budget_exceeded" in msg:
            warn("LLM loop skipped: LiteLLM budget exceeded for the configured key")
            note(f"Error: {e}")
        else:
            fail(f"LLM loop failed: {type(e).__name__}: {e}")

print("\n" + "=" * 60)
print("Verification complete. Review ❌/⚠️ items above.")
print("=" * 60)
