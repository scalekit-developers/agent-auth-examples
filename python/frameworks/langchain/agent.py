"""
LangChain agent with Scalekit-authenticated Gmail tools.
Run: python python/frameworks/langchain/agent.py
"""
import os
import scalekit.client
from dotenv import load_dotenv, find_dotenv
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI

load_dotenv(find_dotenv())

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

tools = actions.langchain.get_tools(
    identifier="user_123",
    connection_names=["gmail"],
)
tool_map = {t.name: t for t in tools}

llm = ChatOpenAI(model=os.getenv("LITELLM_MODEL", "claude-sonnet-4-6")).bind_tools(tools)
messages = [HumanMessage("Fetch my last 5 unread emails and summarize them")]

while True:
    response = llm.invoke(messages)
    messages.append(response)
    if not response.tool_calls:
        print(response.content)
        break
    for tool_call in response.tool_calls:
        result = tool_map[tool_call["name"]].invoke(tool_call["args"])
        messages.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))
