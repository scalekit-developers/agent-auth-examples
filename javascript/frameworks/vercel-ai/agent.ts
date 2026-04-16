/**
 * Vercel AI SDK agent with Scalekit-authenticated Gmail tools.
 * Run: npx tsx javascript/frameworks/vercel-ai/agent.ts
 */
import { ScalekitClient } from '@scalekit-sdk/node'
import { ConnectorStatus } from '@scalekit-sdk/node/lib/pkg/grpc/scalekit/v1/connected_accounts/connected_accounts_pb.js'
import { createOpenAICompatible } from '@ai-sdk/openai-compatible'
import { generateText, jsonSchema, stepCountIs, tool } from 'ai'
import 'dotenv/config'

const scalekit = new ScalekitClient(
  process.env.SCALEKIT_ENVIRONMENT_URL!,
  process.env.SCALEKIT_CLIENT_ID!,
  process.env.SCALEKIT_CLIENT_SECRET!,
)

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

const { tools: scopedTools } = await scalekit.tools.listScopedTools('user_123', {
  filter: { connectionNames: ['gmail'] },
})

const createTool = tool as unknown as (config: Record<string, unknown>) => unknown

const tools = Object.fromEntries(
  scopedTools
    .map((scopedTool) => scopedTool.tool?.definition)
    .filter((definition): definition is NonNullable<typeof definition> => Boolean(definition?.name))
    .map((definition) => [
      String(definition.name),
      createTool({
        description: String(definition.description ?? ''),
        parameters: jsonSchema((definition.input_schema ?? { type: 'object', properties: {} }) as never),
        execute: async (args: Record<string, unknown>) => {
          const result = await scalekit.actions.executeTool({
            toolName: String(definition.name),
            identifier: 'user_123',
            toolInput: args,
          })
          return result.data
        },
      }),
    ]),
)

const provider = createOpenAICompatible({
  name: 'litellm',
  baseURL: process.env.OPENAI_BASE_URL!,
  apiKey: process.env.OPENAI_API_KEY!,
})

const { text } = await generateText({
  model: provider(process.env.OPENAI_MODEL || 'claude-sonnet-4-6'),
  tools: tools as never,
  stopWhen: stepCountIs(5) as never,
  prompt: 'Fetch my last 5 unread emails and summarize them',
})
console.log(text)
