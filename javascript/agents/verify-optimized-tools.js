/**
 * verify-optimized-tools.js
 * --------------------------
 * Verifies the code snippets in scalekit-optimized-tools.mdx, steps 1–6.
 *
 * Checkpoints:
 *   ✅ Step 2: SDK initializes from env vars
 *   ✅ Step 3: listTools returns results; listScopedTools returns per-user tools with inputSchema
 *   ✅ Step 4: getOrCreateConnectedAccount + getConnectedAccount work
 *   ✅ Step 1 (negative): executing a tool for an unknown user raises ScalekitNotFoundException
 *   ✅ Step 5: executeTool runs a read-only tool per connector (gmail, github, linear)
 *   ✅ Step 6: Anthropic LLM loop via LiteLLM proxy completes with at least one tool_use
 *
 * Run (from javascript/ directory):
 *   node agents/verify-optimized-tools.js
 *
 * Required env vars (.env at repo root, loaded via path override):
 *   SCALEKIT_ENVIRONMENT_URL  SCALEKIT_CLIENT_ID  SCALEKIT_CLIENT_SECRET
 *   LITELLM_BASE_URL          LITELLM_API_KEY
 */

import { config as dotenvConfig } from 'dotenv';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import readline from 'readline/promises';
import { ScalekitClient } from '@scalekit-sdk/node';
import { ScalekitNotFoundException } from '@scalekit-sdk/node';
import Anthropic from '@anthropic-ai/sdk';

// Load root .env (two levels up from javascript/agents/)
const __dirname = dirname(fileURLToPath(import.meta.url));
dotenvConfig({ path: resolve(__dirname, '../../.env') });

// ── Helpers ───────────────────────────────────────────────────────────────────

const ok   = (msg) => console.log(`  ✅ ${msg}`);
const fail = (msg) => console.log(`  ❌ ${msg}`);
const warn = (msg) => console.log(`  ⚠️  ${msg}`);
const note = (msg) => console.log(`     ${msg}`);
const section = (title) => console.log(`\n${'─'.repeat(60)}\n${title}\n${'─'.repeat(60)}`);

const IDENTIFIER = 'user_123';
const CONNECTOR_TARGETS = [
  { label: 'gmail', connectionName: process.env.GMAIL_CONNECTION_NAME ?? 'gmail' },
  { label: 'github', connectionName: process.env.GITHUB_CONNECTION_NAME ?? 'github-qkHFhMip' },
  { label: 'linear', connectionName: process.env.LINEAR_CONNECTION_NAME ?? 'linear' },
];
const READ_PREFIXES = ['list_', 'fetch_', 'get_', 'search_', 'read_'];
const toolDef = (scopedTool) => scopedTool?.tool?.definition ?? {};
const MODEL_NAME = process.env.LITELLM_MODEL ?? 'claude-sonnet-4-6';
const INTERACTIVE = (process.env.VERIFY_INTERACTIVE ?? 'true') === 'true' && process.stdin.isTTY;
const ACTIVE_STATUS = new Set(['ACTIVE', 1]);
const fmtTime = (value) => {
  if (!value) return 'n/a';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'bigint') return String(value);
  if (typeof value === 'object' && value.seconds !== undefined) {
    const sec = typeof value.seconds === 'bigint' ? Number(value.seconds) : value.seconds;
    if (Number.isFinite(sec)) return new Date(sec * 1000).toISOString();
    return String(value.seconds);
  }
  return String(value);
};
const statusLabel = (status) => {
  if (status === 1) return 'ACTIVE';
  if (status === 3) return 'PENDING_AUTH';
  if (status === 0) return 'STATUS_UNSPECIFIED';
  return String(status);
};

// ── STEP 2: Initialize SDK client ─────────────────────────────────────────────

section('Step 2 — Initialize SDK client');

const scalekit = new ScalekitClient(
  process.env.SCALEKIT_ENVIRONMENT_URL,
  process.env.SCALEKIT_CLIENT_ID,
  process.env.SCALEKIT_CLIENT_SECRET,
);
const actions = scalekit.actions;

ok('SDK initialized — scalekit.actions ready');

// ── STEP 3: Discover tools ─────────────────────────────────────────────────────

section('Step 3 — Discover tools');

const allToolsResp = await scalekit.tools.listTools();
ok(`listTools — ${(allToolsResp.toolNames ?? []).length} tools in workspace`);

const scopedByConnector = {};
for (const target of CONNECTOR_TARGETS) {
  const { label, connectionName } = target;
  let tools = [];
  try {
    ({ tools } = await scalekit.tools.listScopedTools(IDENTIFIER, {
      filter: { connectionNames: [connectionName] },
    }));
  } catch (err) {
    if (err instanceof ScalekitNotFoundException) {
      warn(`listScopedTools(${label} -> ${connectionName}) not found for identifier=${IDENTIFIER}; continuing`);
      note(`Error: ${err.message}`);
      scopedByConnector[label] = [];
      continue;
    }
    throw err;
  }
  scopedByConnector[label] = tools;
  const names = tools.slice(0, 5).map(t => toolDef(t).name).filter(Boolean);
  ok(`listScopedTools(${label} -> ${connectionName}) — ${tools.length} tools: [${names.join(', ')}]`);
  if (tools.length > 0) {
    const firstDef = toolDef(tools[0]);
    const schema = firstDef.input_schema;
    if (schema && typeof schema === 'object' && schema.properties) {
      ok(`  inputSchema for '${firstDef.name}': properties=[${Object.keys(schema.properties).slice(0, 5).join(', ')}]`);
    } else {
      note(`inputSchema for '${firstDef.name}': ${JSON.stringify(schema)}`);
    }
  }
}

// ── STEP 4: Authorize user ─────────────────────────────────────────────────────

section('Step 4 — Authorize user');

const rl = INTERACTIVE
  ? readline.createInterface({ input: process.stdin, output: process.stdout })
  : null;

for (const target of CONNECTOR_TARGETS) {
  const { label, connectionName } = target;
  let resp;
  try {
    resp = await actions.getOrCreateConnectedAccount({
      connectionName,
      identifier: IDENTIFIER,
    });
  } catch (err) {
    if (err instanceof ScalekitNotFoundException) {
      warn(`${label} (${connectionName}): connection not found in workspace; skipping auth/execute for this connector`);
      note(`Error: ${err.message}`);
      scopedByConnector[label] = [];
      continue;
    }
    throw err;
  }
  const account = resp.connectedAccount;
  const status = account?.status ?? 'unknown';

  if (ACTIVE_STATUS.has(status)) {
    ok(`${label}: connected account ACTIVE (id=${account?.id})`);
    // inspect sensitive details — server-side only
    const details = await actions.getConnectedAccount({
      connectionName,
      identifier: IDENTIFIER,
    });
    const ca = details.connectedAccount;
    ok(`  getConnectedAccount — tokenExpiresAt=${fmtTime(ca?.tokenExpiresAt)}, lastUsedAt=${fmtTime(ca?.lastUsedAt)}`);
  } else {
    const linkResp = await actions.getAuthorizationLink({
      connectionName,
      identifier: IDENTIFIER,
    });
    console.log(`\n  ⚠️  ${label} not ACTIVE (status=${statusLabel(status)})`);
    console.log(`  Authorize here: ${linkResp.link}`);
    if (INTERACTIVE && rl) {
      await rl.question(`  Press Enter after authorizing ${label}…\n`);
    } else {
      warn('Non-interactive mode: skipping wait for manual authorization');
      continue;
    }
    // re-check
    const resp2 = await actions.getOrCreateConnectedAccount({ connectionName, identifier: IDENTIFIER });
    const a2 = resp2.connectedAccount;
    if (a2?.status === 'ACTIVE') {
      ok(`${label}: now ACTIVE`);
    } else {
      fail(`${label}: still not ACTIVE (status=${a2?.status ?? 'unknown'}) — skipping execute`);
    }
  }
}
if (rl) {
  rl.close();
}

// ── STEP 1 (negative): Missing connection raises ScalekitNotFoundException ─────

section('Step 1 (negative) — Missing connection raises ScalekitNotFoundException');

const knownToolName = [
  ...(scopedByConnector.gmail ?? []),
  ...(scopedByConnector.github ?? []),
  ...(scopedByConnector.linear ?? []),
].map(t => toolDef(t).name).find(Boolean) ?? 'gmail_fetch_mails';

try {
  await actions.executeTool({
    toolName: knownToolName,
    toolInput: { maxResults: 1 },
    identifier: '__verify_nonexistent_user_xyz__',
  });
  fail('Expected ScalekitNotFoundException — got success instead');
} catch (err) {
  if (err instanceof ScalekitNotFoundException) {
    ok(`ScalekitNotFoundException raised as expected`);
    note(`Error: ${err.message}`);
  } else {
    const msg = `${err.message ?? ''}`.toLowerCase();
    if (msg.includes('resource_not_found') || msg.includes('not_found')) {
      ok(`Resource-not-found style error raised as expected (${err.constructor.name})`);
      note(`Error: ${err.message}`);
    } else {
      warn(`Got ${err.constructor.name} (not ScalekitNotFoundException): ${err.message}`);
      note("The mdx claims 'resource not found' — actual exception type may differ");
    }
  }
}

// ── STEP 5: Execute tool per connector ────────────────────────────────────────

section('Step 5 — Execute tool across connectors');

for (const target of CONNECTOR_TARGETS) {
  const { label } = target;
  const toolsForConn = scopedByConnector[label] ?? [];
  if (toolsForConn.length === 0) {
    warn(`${label}: no scoped tools — skipping execute`);
    continue;
  }

  // pick first read-only tool by name prefix; fall back to first available
  const candidate = toolsForConn.find(t => {
    const name = toolDef(t).name ?? '';
    return READ_PREFIXES.some(p => name.startsWith(p));
  })
    ?? toolsForConn[0];
  const candidateName = toolDef(candidate).name;

  // build minimal required input from JSON Schema
  const schema = toolDef(candidate).input_schema ?? {};
  const requiredFields = schema.required ?? [];
  const props = schema.properties ?? {};
  const toolInput = {};
  for (const field of requiredFields) {
    const fdef = props[field] ?? {};
    let ftype = fdef.type ?? 'string';
    if (Array.isArray(ftype)) {
      ftype = ftype.find(t => t !== 'null') ?? 'string';
    }
    if (ftype === 'integer')      toolInput[field] = 1;
    else if (ftype === 'boolean') toolInput[field] = false;
    else                          toolInput[field] = '';
  }

  try {
    const result = await actions.executeTool({
      toolName: candidateName,
      toolInput,
      identifier: IDENTIFIER,
    });
    const keys = result.data && typeof result.data === 'object' ? Object.keys(result.data) : [];
    const dataShape = keys.length > 0 ? `[${keys.join(', ')}]` : typeof result.data;
    ok(`${label}: executeTool('${candidateName}') → data keys: ${dataShape}`);
  } catch (err) {
    const msg = `${err.message ?? ''}`.toLowerCase();
    if (msg.includes('not active')) {
      warn(`${label}: executeTool('${candidateName}') skipped because connected account is not ACTIVE`);
    } else {
      fail(`${label}: executeTool('${candidateName}') raised ${err.constructor.name}: ${err.message}`);
    }
  }

  // surface real tool names for mdx verification
  note(`Actual ${label} tool names: [${toolsForConn.slice(0, 5).map(t => toolDef(t).name).filter(Boolean).join(', ')}]`);
}

// ── STEP 6: Full LLM tool-calling loop (Anthropic SDK → LiteLLM) ─────────────

section('Step 6 — Full LLM tool-calling loop');

const litellmUrl = process.env.LITELLM_BASE_URL;
const litellmKey = process.env.LITELLM_API_KEY;

if (!litellmUrl || !litellmKey) {
  warn('LITELLM_BASE_URL or LITELLM_API_KEY not set — skipping step 6');
} else {
  try {
    // 1. Fetch scoped gmail tools
    const gmailConnectionName = CONNECTOR_TARGETS.find(t => t.label === 'gmail')?.connectionName ?? 'gmail';
    const { tools: scopedTools } = await scalekit.tools.listScopedTools(IDENTIFIER, {
      filter: { connectionNames: [gmailConnectionName] },
    });
    // Reshape to Anthropic tool format — matches mdx exactly
    const llmTools = scopedTools.map(t => ({
      name: toolDef(t).name,
      description: toolDef(t).description,
      input_schema: toolDef(t).input_schema ?? {},
    })).filter(t => t.name);

    // 2. Send user message to the LLM with tools attached
    const anthropic = new Anthropic({ baseURL: litellmUrl, apiKey: litellmKey });
    const messages = [{ role: 'user', content: 'Summarize my last 5 unread emails' }];

    const response = await anthropic.messages.create({
      model: MODEL_NAME,
      max_tokens: 1024,
      tools: llmTools,
      messages,
    });

    // 3. Execute any tool_use blocks the LLM requested
    let toolUseCount = 0;
    for (const block of response.content) {
      if (block.type === 'tool_use') {
        toolUseCount++;
        const toolResult = await scalekit.actions.executeTool({
          toolName: block.name,
          toolInput: block.input,
          identifier: IDENTIFIER,
        });
        // 4. Append result back for the final completion
        messages.push({ role: 'assistant', content: response.content });
        messages.push({
          role: 'user',
          content: [{
            type: 'tool_result',
            tool_use_id: block.id,
            content: JSON.stringify(toolResult.data),
          }],
        });
      }
    }

    if (toolUseCount > 0) {
      const final = await anthropic.messages.create({
        model: MODEL_NAME,
        max_tokens: 1024,
        tools: llmTools,
        messages,
      });
      const finalText = final.content.find(b => b.type === 'text')?.text ?? '';
      if (finalText) {
        ok(`LLM loop: ${toolUseCount} tool_use(s) executed, final text received (${finalText.length} chars)`);
        note(`Final text (first 300 chars): ${finalText.slice(0, 300)}`);
      } else {
        warn('LLM loop: tool_use executed but no final text in response');
      }
    } else {
      warn(`LLM loop: no tool_use blocks (stop_reason=${response.stop_reason}) — LLM may not have called a tool`);
      note(`Content types: [${response.content.map(b => b.type).join(', ')}]`);
    }
  } catch (err) {
    const msg = `${err.message ?? ''}`.toLowerCase();
    if (msg.includes('budget has been exceeded') || msg.includes('budget_exceeded')) {
      warn('LLM loop skipped: LiteLLM budget exceeded for the configured key');
      note(`Error: ${err.message}`);
    } else {
      fail(`LLM loop failed: ${err.constructor.name}: ${err.message}`);
    }
  }
}

console.log('\n' + '='.repeat(60));
console.log('Verification complete. Review ❌/⚠️ items above.');
console.log('='.repeat(60));
