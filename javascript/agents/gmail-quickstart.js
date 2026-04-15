/**
 * Gmail Agent Auth quickstart: connect a Gmail account via Scalekit and list unread messages.
 *
 * Run: node agents/gmail-quickstart.js (from the javascript/ directory)
 * Setup: copy .env.example to .env and set SCALEKIT_* variables. In Scalekit, create a
 *        Gmail connection named "gmail" (Agent Auth → Connections).
 *
 * Dependencies: npm install (see package.json)
 */
import { ScalekitClient } from '@scalekit-sdk/node';
import { ConnectorStatus } from '@scalekit-sdk/node/lib/pkg/grpc/scalekit/v1/connected_accounts/connected_accounts_pb.js';
import 'dotenv/config';

const envUrl = process.env.SCALEKIT_ENVIRONMENT_URL;
const clientId = process.env.SCALEKIT_CLIENT_ID;
const clientSecret = process.env.SCALEKIT_CLIENT_SECRET;
if (!envUrl || !clientId || !clientSecret) {
  console.error(
    'Missing env: set SCALEKIT_ENVIRONMENT_URL, SCALEKIT_CLIENT_ID, and SCALEKIT_CLIENT_SECRET in .env'
  );
  process.exit(1);
}

const scalekit = new ScalekitClient(envUrl, clientId, clientSecret);

const actions = scalekit.actions;

// Create or retrieve the user's connected Gmail account
const response = await actions.getOrCreateConnectedAccount({
  connectionName: 'hubspot',
  identifier: 'user_123', // Replace with your system's unique user ID
});

const connectedAccount = response.connectedAccount;
console.log('Connected account created:', connectedAccount?.id);

// Generate authorization link if user hasn't authorized or token is expired
if (connectedAccount?.status !== ConnectorStatus.ACTIVE) {
  console.log('gmail is not connected:', connectedAccount?.status);
  const linkResponse = await actions.getAuthorizationLink({
    connectionName: 'gmail',
    identifier: 'user_123',
  });
  console.log(
    'Open this link to authorize Gmail, then run this script again:',
    linkResponse.link
  );
  process.exit(0);
}

// // Fetch up to 5 unread messages via Scalekit proxy (requires ACTIVE connection)
// const result = await actions.request({
//   connectionName: 'gmail',
//   identifier: 'user_123',
//   path: '/gmail/v1/users/me/messages',
//   method: 'GET',
//   queryParams: { q: 'is:unread', maxResults: 5 },
// });
// console.log(result.data);

const toolResponse = await actions.executeTool({
  toolName: 'gmail_fetch_mails',
  connectedAccountId: connectedAccount?.id,
  toolInput: {
    query: 'is:unread',
    max_results: 5,
  },
});
console.log('Recent emails:', toolResponse.data);
