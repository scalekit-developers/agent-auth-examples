/**
 * Mastra agent with Scalekit-authenticated Gmail tools via MCP.
 * Run: npx tsx javascript/frameworks/mastra/agent.ts
 *
 * Prerequisite: set SCALEKIT_MCP_URL in .env
 */
import { createOpenAICompatible } from '@ai-sdk/openai-compatible'
import { Agent } from '@mastra/core/agent'
import { MCPClient } from '@mastra/mcp'
import 'dotenv/config'

const mcpUrl = process.env.SCALEKIT_MCP_URL
if (!mcpUrl) {
  console.error('SCALEKIT_MCP_URL not set. Generate it with actions.mcp.ensure_instance() and add to .env')
  process.exit(1)
}

const mcp = new MCPClient({
  servers: {
    scalekit: { url: new URL(mcpUrl) },
  },
})

const tools = await mcp.listTools()

const provider = createOpenAICompatible({
  name: 'litellm',
  baseURL: process.env.OPENAI_BASE_URL!,
  apiKey: process.env.OPENAI_API_KEY!,
})

const agent = new Agent({
  id: 'gmail-assistant',
  name: 'gmail_assistant',
  instructions: 'You are a helpful Gmail assistant.',
  model: provider(process.env.OPENAI_MODEL || 'claude-sonnet-4-6') as never,
  tools,
})

const result = await agent.generate('Fetch my last 5 unread emails and summarize them')
console.log(result.text)

await mcp.disconnect()
