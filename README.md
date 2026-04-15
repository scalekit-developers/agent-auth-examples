# Scalekit Agent Auth Examples

This repository hosts examples of the agent auth capabilities of Scalekit.

**Note: This project is a work in progress.**

## What is Agent Auth?

Scalekit Agent Auth handles the full OAuth lifecycle — authorization, token storage, and automatic refresh — so AI agents can act on behalf of users in Gmail, Google Calendar, Slack, Notion, and other connectors.

## Examples

| Language | Use Case | Connector(s) | File |
|----------|----------|--------------|------|
| Python | AI Email Triage & Draft Replies | Gmail | [python/email_triage_agent.py](python/email_triage_agent.py) |
| Python | Meeting Scheduler | Google Calendar + Gmail | [python/meeting_scheduler_agent.py](python/meeting_scheduler_agent.py) |
| Python | Daily Briefing / Morning Digest | Gmail + Google Calendar | [python/daily_briefing_agent.py](python/daily_briefing_agent.py) |

## Verification scripts for `scalekit-optimized-tools.mdx`

Use these scripts when you want to test the implementation shown in `src/content/docs/agentkit/tools/scalekit-optimized-tools.mdx` end to end.

| Language | Scope | File |
|----------|-------|------|
| Python | Steps 1-6 verifier | [python/validate_scalekit_optimized_tools_flow.py](python/validate_scalekit_optimized_tools_flow.py) |
| Python | Step 7 LangChain adapter | [python/validate_langchain_scalekit_tools_adapter.py](python/validate_langchain_scalekit_tools_adapter.py) |
| Python | Step 7 Google ADK adapter | [python/validate_google_adk_scalekit_tools_adapter.py](python/validate_google_adk_scalekit_tools_adapter.py) |
| JavaScript (Node) | Steps 1-6 verifier | [javascript/agents/validate-scalekit-optimized-tools-flow.js](javascript/agents/validate-scalekit-optimized-tools-flow.js) |
| JavaScript (Node) | Step 7 Vercel AI SDK adapter | [javascript/agents/validate-vercel-ai-scalekit-tools-adapter.js](javascript/agents/validate-vercel-ai-scalekit-tools-adapter.js) |

## Getting Started

### 1. Set up credentials

```bash
cp .env.example .env
# Edit .env with your values from app.scalekit.com → Developers → Settings → API Credentials
```

### 2. Install dependencies

```bash
cd python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Run an example

```bash
python email_triage_agent.py
python meeting_scheduler_agent.py
python daily_briefing_agent.py
```

## Run the verification scripts

### 1. Install dependencies (Python + Node)

```bash
# Python
cd python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# JavaScript
cd ../javascript
npm install
```

### 2. Configure environment

The scripts read `.env` at the repo root.

Required variables:

- `SCALEKIT_ENVIRONMENT_URL`
- `SCALEKIT_CLIENT_ID`
- `SCALEKIT_CLIENT_SECRET`
- `LITELLM_BASE_URL`
- `LITELLM_API_KEY`

Optional variables:

- `LITELLM_MODEL` (default: `claude-sonnet-4-6`)
- `VERIFY_INTERACTIVE` (`true` or `false`, default: `true`)
- `GMAIL_CONNECTION_NAME` (default: `gmail`)
- `GITHUB_CONNECTION_NAME` (default: `github-qkHFhMip`)
- `LINEAR_CONNECTION_NAME` (default: `linear`)

### 3. Run all verifiers

```bash
# from repo root
source python/.venv/bin/activate
VERIFY_INTERACTIVE=false python python/validate_scalekit_optimized_tools_flow.py
python python/validate_langchain_scalekit_tools_adapter.py
python python/validate_google_adk_scalekit_tools_adapter.py

cd javascript
VERIFY_INTERACTIVE=false node agents/validate-scalekit-optimized-tools-flow.js
node agents/validate-vercel-ai-scalekit-tools-adapter.js
```

Set `VERIFY_INTERACTIVE=true` if you want the scripts to pause and wait for manual connector authorization.

## Understand verifier output

Each script prints checkpoint lines:

- `✅` Passed check
- `⚠️` Expected runtime caveat (for example, connector not active, connection missing, or LiteLLM budget exceeded)
- `❌` Failed check that needs investigation

The Steps 1-6 verifiers map directly to doc sections:

- **Step 1**: negative case for missing user/account
- **Step 2**: SDK initialization
- **Step 3**: tool discovery and schema shape
- **Step 4**: connection status and authorization flow
- **Step 5**: real tool execution across configured connectors
- **Step 6**: LLM tool-calling loop via LiteLLM

The Step 7 adapter scripts validate framework integrations:

- Python: LangChain and Google ADK adapters
- Node: Vercel AI SDK tool-calling adapter

## Use verifier results with docs

After running scripts, use output to update docs safely:

- Confirm real tool names (for example `gmail_fetch_mails` vs `gmail_fetch_emails`)
- Confirm schema fields (`max_results` / `maxResults` drift)
- Confirm real error semantics for missing resources
- Confirm connector names and env var names used in practice

## Dashboard Setup (required for all connectors)

All scripts require a one-time connection setup in the Scalekit Dashboard before running.

1. Go to **Scalekit Dashboard → Agent Auth → Connections**
2. Click **+ Create Connection**
3. Select the connector and set the **Connection Name** exactly as shown below:

| Connector | Connection Name |
|-----------|----------------|
| Gmail | `gmail` |
| GitHub | `github-qkHFhMip` |
| Linear | `linear` |
| Google Calendar | `googlecalendar` |

4. Click **Save**

> The Connection Name must match the `connection_name` value in the script exactly.

## First-Run Authorization

The first time you run a script, the user hasn't authorized access yet. The script will print an authorization link and wait:

```
Authorize access here: https://your-env.scalekit.dev/magicLink/...
Press Enter after completing authorization...
```

1. Open the link in your browser
2. Sign in with the Google account you want to connect
3. Grant the requested permissions
4. Return to the terminal and press **Enter**

On all subsequent runs, Scalekit uses the stored token (auto-refreshed as needed) and skips the authorization step entirely.