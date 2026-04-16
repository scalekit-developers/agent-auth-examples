"""
OpenAI-compatible agent with Scalekit-authenticated Gmail tools.
Run: python python/frameworks/openai/agent.py
"""
import json
import os
import scalekit.client
from dotenv import find_dotenv, load_dotenv
from google.protobuf.json_format import MessageToDict
from openai import OpenAI

load_dotenv(find_dotenv())

scalekit_client = scalekit.client.ScalekitClient(
    client_id=os.getenv("SCALEKIT_CLIENT_ID"),
    client_secret=os.getenv("SCALEKIT_CLIENT_SECRET"),
    env_url=os.getenv("SCALEKIT_ENVIRONMENT_URL"),
)
actions = scalekit_client.actions
client = OpenAI(base_url=os.getenv("OPENAI_BASE_URL"), api_key=os.getenv("OPENAI_API_KEY"))

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
        "type": "function",
        "function": {
            "name": MessageToDict(tool.tool).get("definition", {}).get("name"),
            "description": MessageToDict(tool.tool).get("definition", {}).get("description", ""),
            "parameters": MessageToDict(tool.tool).get("definition", {}).get("input_schema", {}),
        },
    }
    for tool in scoped_response.tools
]

messages = [{"role": "user", "content": "Fetch my last 5 unread emails and summarize them"}]

while True:
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "claude-sonnet-4-6"),
        tools=llm_tools,
        messages=messages,
    )
    message = response.choices[0].message
    if not message.tool_calls:
        print(message.content)
        break

    messages.append(message)
    for tool_call in message.tool_calls:
        result = actions.execute_tool(
            tool_name=tool_call.function.name,
            identifier="user_123",
            tool_input=json.loads(tool_call.function.arguments),
        )
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(result.data),
            }
        )
