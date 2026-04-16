/**
 * Quickstart: fetch last 5 unread Gmail messages via Scalekit.
 * Run: npx tsx javascript/frameworks/quickstart/main.ts
 */
import { ScalekitClient } from '@scalekit-sdk/node'
import { ConnectorStatus } from '@scalekit-sdk/node/lib/pkg/grpc/scalekit/v1/connected_accounts/connected_accounts_pb.js'
import 'dotenv/config'

const scalekit = new ScalekitClient(
  process.env.SCALEKIT_ENVIRONMENT_URL!,
  process.env.SCALEKIT_CLIENT_ID!,
  process.env.SCALEKIT_CLIENT_SECRET!,
)
const actions = scalekit.actions

const response = await actions.getOrCreateConnectedAccount({
  connectionName: 'gmail',
  identifier: 'user_123',
})
const connectedAccount = response.connectedAccount
console.log('Connected account:', connectedAccount?.id, '| status:', connectedAccount?.status)

if (connectedAccount?.status !== ConnectorStatus.ACTIVE) {
  const linkResponse = await actions.getAuthorizationLink({
    connectionName: 'gmail',
    identifier: 'user_123',
  })
  console.log('Authorize Gmail:', linkResponse.link)
  process.exit(0)
}

const toolResponse = await actions.executeTool({
  toolName: 'gmail_fetch_mails',
  connectedAccountId: connectedAccount?.id,
  toolInput: {
    query: 'is:unread',
    max_results: 5,
  },
})
console.log('Recent emails:', toolResponse.data)
