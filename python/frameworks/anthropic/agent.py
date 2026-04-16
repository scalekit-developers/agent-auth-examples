"""
Anthropic Claude agent with Scalekit-authenticated Gmail tools.
Run: python python/frameworks/anthropic/agent.py
"""
import os
import anthropic
import scalekit.client
from dotenv import find_dotenv, load_dotenv
from google.protobuf.json_format import MessageToDict

load_dotenv(find_dotenv())

scalekit_client = scalekit.client.ScalekitClient(
    client_id=os.getenv("SCALEKIT_CLIENT_ID"),
    client_secret=os.getenv("SCALEKIT_CLIENT_SECRET"),
    env_url=os.getenv("SCALEKIT_ENVIRONMENT_URL"),
)
actions = scalekit_client.actions

client = anthropic.Anthropic(
    base_url=os.getenv("ANTHROPIC_BASE_URL"),
    api_key=os.getenv("ANTHROPIC_API_KEY"),
)

response = actions.get_or_create_connected_account(
    connection_name="gmail",
    identifier="user_123",
)
if response.connected_account.status != "ACTIVE":
    link = actions.get_authorization_link(connection_name="gmail", identifier="user_123")
    print("Authorize Gmail:", link.link)
    input("Press Enter after authorizing...")

scoped_response, _ = actions.tools.list_scoped_tools(
    identifier="user_123",
    filter={"connection_names": ["gmail"]},
)

llm_tools = [
    {
        "name": MessageToDict(tool.tool).get("definition", {}).get("name"),
        "description": MessageToDict(tool.tool).get("definition", {}).get("description", ""),
        "input_schema": MessageToDict(tool.tool).get("definition", {}).get("input_schema", {}),
    }
    for tool in scoped_response.tools
]

messages = [{"role": "user", "content": "Fetch my last 5 unread emails and summarize them"}]

while True:
    response = client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        max_tokens=1024,
        tools=llm_tools,
        messages=messages,
    )
    if response.stop_reason == "end_turn":
        print(response.content[0].text)
        break

    tool_results = []
    for block in response.content:
        if block.type == "tool_use":
            result = actions.execute_tool(
                tool_name=block.name,
                identifier="user_123",
                tool_input=block.input,
            )
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result.data),
                }
            )

    messages.append({"role": "assistant", "content": response.content})
    messages.append({"role": "user", "content": tool_results})
