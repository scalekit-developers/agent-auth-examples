"""
Quickstart: fetch last 5 unread Gmail messages via Scalekit.
Run: python python/frameworks/quickstart/main.py
"""
import os
import scalekit.client
from dotenv import load_dotenv, find_dotenv

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
connected_account = response.connected_account
print(f"Connected account: {connected_account.id} | status: {connected_account.status}")

if connected_account.status != "ACTIVE":
    link_response = actions.get_authorization_link(
        connection_name="gmail",
        identifier="user_123",
    )
    print(f"Authorize Gmail: {link_response.link}")
    input("Press Enter after authorizing Gmail...")

tool_response = actions.execute_tool(
    tool_name="gmail_fetch_mails",
    identifier="user_123",
    tool_input={
        "query": "is:unread",
        "max_results": 5,
    },
)
print(tool_response)
