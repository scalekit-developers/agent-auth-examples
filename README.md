# Scalekit Agent Auth Examples

This repository hosts examples of the agent auth capabilities of Scalekit.

**Note: This project is a work in progress.**

## What is Agent Auth?

Scalekit Agent Auth handles the full OAuth lifecycle — authorization, token storage, and automatic refresh — so AI agents can act on behalf of users in Gmail, Google Calendar, Slack, Notion, and other connectors.

## Examples

| Language | Connector | File |
|----------|-----------|------|
| Python | Gmail | [python/google_agent.py](python/google_agent.py) |
| Python | Google Calendar | [python/google_calendar_agent.py](python/google_calendar_agent.py) |

## Getting Started

### 1. Set up credentials

```bash
cp .env.example .env
# Edit .env with your values from app.scalekit.com → Developers → Settings → API Credentials
```

### 2. Install dependencies

```bash
# Python
pip install scalekit-sdk-python python-dotenv requests
```

### 3. Run an example

```bash
python python/google_agent.py
python python/google_calendar_agent.py
```

## Dashboard Setup

> Gmail works out of the box. All other connectors require a one-time setup.

For Google Calendar (and other connectors):
1. Go to **Scalekit Dashboard → Agent Auth → Connections**
2. Click **+ Create Connection**
3. Select the connector and set a **Connection Name** (e.g. `google-calendar`)
4. Click **Save**

The Connection Name must match the `connection_name` used in your code.