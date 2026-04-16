/**
 * OpenAI-compatible agent with Scalekit-authenticated Gmail tools.
 * Run: npx tsx javascript/frameworks/openai/agent.ts
 */
import { ScalekitClient } from '@scalekit-sdk/node'
import { ConnectorStatus } from '@scalekit-sdk/node/lib/pkg/grpc/scalekit/v1/connected_accounts/connected_accounts_pb.js'
import OpenAI from 'openai'
import 'dotenv/config'

const scalekit = new ScalekitClient(
  process.env.SCALEKIT_ENVIRONMENT_URL!,
  process.env.SCALEKIT_CLIENT_ID!,
  process.env.SCALEKIT_CLIENT_SECRET!,
)

const openai = new OpenAI({
  baseURL: process.env.OPENAI_BASE_URL,
  apiKey: process.env.OPENAI_API_KEY,
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
const llmTools: OpenAI.ChatCompletionTool[] = tools
  .map((tool) => tool.tool?.definition)
  .filter((definition): definition is NonNullable<typeof definition> => Boolean(definition?.name))
  .map((definition) => ({
    type: 'function',
    function: {
      name: String(definition.name),
      description: String(definition.description ?? ''),
      parameters: (definition.input_schema ?? { type: 'object', properties: {} }) as Record<string, unknown>,
    },
  }))

const messages: OpenAI.ChatCompletionMessageParam[] = [
  { role: 'user', content: 'Fetch my last 5 unread emails and summarize them' },
]

while (true) {
  const response = await openai.chat.completions.create({
    model: process.env.OPENAI_MODEL || 'claude-sonnet-4-6',
    tools: llmTools,
    messages,
  })
  const message = response.choices[0].message
  if (!message.tool_calls?.length) {
    console.log(message.content)
    break
  }

  messages.push(message)
  for (const toolCall of message.tool_calls) {
    if (!('function' in toolCall)) {
      continue
    }
    const result = await scalekit.actions.executeTool({
      toolName: toolCall.function.name,
      identifier: 'user_123',
      toolInput: JSON.parse(toolCall.function.arguments),
    })
    messages.push({ role: 'tool', tool_call_id: toolCall.id, content: JSON.stringify(result.data) })
  }
}
