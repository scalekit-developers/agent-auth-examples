/**
 * verify-vercel-ai-tools.js
 * --------------------------
 * Verifies step 7 of scalekit-optimized-tools.mdx using the Vercel AI SDK.
 *
 * Reshapes scalekit.tools.listScopedTools output into Vercel AI SDK tool() objects
 * (using jsonSchema() to avoid Zod conversion), then runs generateText via a
 * LiteLLM proxy with @ai-sdk/openai-compatible.
 *
 * Run (from javascript/ directory):
 *   node agents/verify-vercel-ai-tools.js
 *
 * Required env vars (.env at repo root, loaded via path override):
 *   SCALEKIT_ENVIRONMENT_URL  SCALEKIT_CLIENT_ID  SCALEKIT_CLIENT_SECRET
 *   LITELLM_BASE_URL          LITELLM_API_KEY
 *
 * Required packages:
 *   npm install ai @ai-sdk/openai-compatible
 */

import { config as dotenvConfig } from 'dotenv';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { ScalekitClient } from '@scalekit-sdk/node';
import { generateText, tool, jsonSchema } from 'ai';
import { createOpenAICompatible } from '@ai-sdk/openai-compatible';

// Load root .env (two levels up from javascript/agents/)
const __dirname = dirname(fileURLToPath(import.meta.url));
dotenvConfig({ path: resolve(__dirname, '../../.env') });

console.log('='.repeat(60));
console.log('Step 7 Vercel AI SDK adapter verification');
console.log('='.repeat(60));

const IDENTIFIER = 'user_123';
const toolDef = (scopedTool) => scopedTool?.tool?.definition ?? {};
const MODEL_NAME = process.env.LITELLM_MODEL ?? 'claude-sonnet-4-6';

// Initialize Scalekit
const scalekit = new ScalekitClient(
  process.env.SCALEKIT_ENVIRONMENT_URL,
  process.env.SCALEKIT_CLIENT_ID,
  process.env.SCALEKIT_CLIENT_SECRET,
);

// 1. Fetch scoped Gmail tools for this user
const { tools: scopedTools } = await scalekit.tools.listScopedTools(IDENTIFIER, {
  filter: { connectionNames: ['gmail'] },
});

if (scopedTools.length === 0) {
  console.log('  ❌ No scoped tools returned for gmail — cannot continue');
  process.exit(1);
}

console.log(`  ✅ listScopedTools(gmail) returned ${scopedTools.length} tools: ` +
  `[${scopedTools.slice(0, 5).map(t => toolDef(t).name).filter(Boolean).join(', ')}]`);

// 2. Reshape into Vercel AI SDK tool() objects using jsonSchema() (no Zod needed)
const tools = {};
for (const t of scopedTools) {
  const definition = toolDef(t);
  if (!definition.name) {
    continue;
  }
  tools[definition.name] = tool({
    description: definition.description,
    parameters: jsonSchema(definition.input_schema ?? { type: 'object', properties: {} }),
    execute: async (args) => {
      const result = await scalekit.actions.executeTool({
        toolName: definition.name,
        toolInput: args,
        identifier: IDENTIFIER,
      });
      return result.data;
    },
  });
}

console.log(`  ✅ Reshaped ${Object.keys(tools).length} tools into Vercel AI SDK format`);

// 3. Create OpenAI-compatible model via LiteLLM proxy
const litellm = createOpenAICompatible({
  baseURL: process.env.LITELLM_BASE_URL,
  apiKey: process.env.LITELLM_API_KEY,
  name: 'litellm',
});

// 4. Run generateText with tool calling (maxSteps allows multi-turn tool use)
const result = await generateText({
  model: litellm(MODEL_NAME),
  tools,
  maxSteps: 5,
  prompt: 'list my 3 most recent emails',
});

// 5. Verify output
const { text, toolCalls, toolResults, steps } = result;

const totalToolCalls = steps.flatMap(s => s.toolCalls ?? []).length;

if (totalToolCalls > 0) {
  console.log(`  ✅ generateText: ${totalToolCalls} tool call(s) executed across ${steps.length} step(s)`);
  for (const step of steps) {
    for (const tc of (step.toolCalls ?? [])) {
      console.log(`     → tool_use: ${tc.toolName}(${JSON.stringify(tc.args).slice(0, 80)})`);
    }
  }
}

if (text) {
  console.log(`  ✅ Final text received (${text.length} chars)`);
  console.log(`     Output (first 300 chars): ${text.slice(0, 300)}`);
} else if (totalToolCalls === 0) {
  console.log('  ❌ No tool calls and no final text — check LiteLLM routing and model name');
}

console.log('\n' + '='.repeat(60));
console.log('Verification complete.');
console.log('='.repeat(60));
