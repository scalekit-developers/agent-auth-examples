"""
CrewAI agent with Scalekit-authenticated Gmail tools via MCP.
Run: python python/frameworks/crewai/agent.py
"""
import os
from typing import Any, Optional
import scalekit.client
from crewai import Agent, Crew, LLM, Task
from crewai_tools import MCPServerAdapter
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

# Patch CrewAI schema conversion to support nullable tool schema fields.
import crewai.utilities.pydantic_schema_utils as _schema_mod

_orig = _schema_mod._json_schema_to_pydantic_type


def _patched(json_schema: dict[str, Any], root_schema: dict[str, Any], **kwargs: Any) -> Any:
    type_ = json_schema.get("type")
    if isinstance(type_, list):
        non_null = [t for t in type_ if t != "null"]
        has_null = "null" in type_
        inner = _orig(
            {**json_schema, "type": non_null[0] if non_null else "string"},
            root_schema,
            **kwargs,
        )
        return Optional[inner] if has_null else inner  # type: ignore[return-value]
    return _orig(json_schema, root_schema, **kwargs)


_schema_mod._json_schema_to_pydantic_type = _patched

scalekit_client = scalekit.client.ScalekitClient(
    client_id=os.getenv("SCALEKIT_CLIENT_ID"),
    client_secret=os.getenv("SCALEKIT_CLIENT_SECRET"),
    env_url=os.getenv("SCALEKIT_ENVIRONMENT_URL"),
)
actions = scalekit_client.actions

response = actions.get_or_create_connected_account(
    connection_name="gmail",
    identifier="user_123",
)
if response.connected_account.status != "ACTIVE":
    link = actions.get_authorization_link(connection_name="gmail", identifier="user_123")
    print("Authorize Gmail:", link.link)
    input("Press Enter after authorizing...")

inst_response = actions.mcp.ensure_instance(
    config_name=os.getenv("SCALEKIT_MCP_CONFIG_NAME", "gmail-user-tools"),
    user_identifier="user_123",
)
mcp_url = inst_response.instance.url

with MCPServerAdapter({"url": mcp_url, "transport": "streamable-http"}) as mcp_tools:
    agent = Agent(
        role="Email Assistant",
        goal="Fetch and summarize the user's unread emails",
        backstory="You are a helpful assistant with access to the user's Gmail inbox.",
        tools=mcp_tools,
        llm=LLM(
            model=os.getenv("OPENAI_MODEL", "claude-sonnet-4-6"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            api_key=os.getenv("OPENAI_API_KEY"),
        ),
        verbose=True,
    )

    task = Task(
        description="Fetch the last 5 unread emails and provide a brief summary of each.",
        expected_output="A list of 5 unread emails with subject, sender, and a one-sentence summary.",
        agent=agent,
    )

    result = Crew(agents=[agent], tasks=[task]).kickoff()
    print(result)
