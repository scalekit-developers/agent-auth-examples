/**
 * Anthropic Claude agent with Scalekit-authenticated Gmail tools.
 * Run: npx tsx javascript/frameworks/anthropic/agent.ts
 */
import { ScalekitClient } from '@scalekit-sdk/node'
import { ConnectorStatus } from '@scalekit-sdk/node/lib/pkg/grpc/scalekit/v1/connected_accounts/connected_accounts_pb.js'
import Anthropic from '@anthropic-ai/sdk'
import 'dotenv/config'

const scalekit = new ScalekitClient(
  process.env.SCALEKIT_ENVIRONMENT_URL!,
  process.env.SCALEKIT_CLIENT_ID!,
  process.env.SCALEKIT_CLIENT_SECRET!,
)

const anthropic = new Anthropic({
  baseURL: process.env.ANTHROPIC_BASE_URL,
  apiKey: process.env.ANTHROPIC_API_KEY,
})

const { connectedAccount } = await scalekit.actions.getOrCreateConnectedAccount({
  connectionName: 'gmail',
  identifier: 'user_123',
})

if (connectedAccount?.status !== ConnectorStatus.ACTIVE) {
  const { link } = await scalekit.actions.getAuthorizationLink({
    connectionName: 'gmail',
    identifier: 'user_123',
  })
  console.log('Authorize Gmail:', link)
  process.exit(0)
}

const { tools } = await scalekit.tools.listScopedTools('user_123', {
  filter: { connectionNames: ['gmail'] },
})
const llmTools = tools
  .map((tool) => tool.tool?.definition)
  .filter((definition): definition is NonNullable<typeof definition> => Boolean(definition?.name))
  .map((definition) => ({
    name: String(definition.name),
    description: String(definition.description ?? ''),
    input_schema: (definition.input_schema ?? { type: 'object', properties: {} }) as Record<string, unknown>,
  }))

const messages: Anthropic.MessageParam[] = [
  { role: 'user', content: 'Fetch my last 5 unread emails and summarize them' },
]

while (true) {
  const response = await anthropic.messages.create({
    model: process.env.ANTHROPIC_MODEL || 'claude-sonnet-4-6',
    max_tokens: 1024,
    tools: llmTools as never,
    messages,
  })

  if (response.stop_reason === 'end_turn') {
    const text = response.content.find((block) => block.type === 'text')
    if (text?.type === 'text') console.log(text.text)
    break
  }

  const toolResults: Anthropic.ToolResultBlockParam[] = []
  for (const block of response.content) {
    if (block.type === 'tool_use') {
      const result = await scalekit.actions.executeTool({
        toolName: block.name,
        identifier: 'user_123',
        toolInput: block.input as Record<string, unknown>,
      })
      toolResults.push({
        type: 'tool_result',
        tool_use_id: block.id,
        content: JSON.stringify(result.data),
      })
    }
  }

  messages.push({ role: 'assistant', content: response.content })
  messages.push({ role: 'user', content: toolResults })
}
