# Returns & Refunds Assistant - Streamlit UI

A chat interface for the Returns & Refunds Assistant agent, with Cognito authentication and AgentCore Runtime integration.

## Features

- **Cognito Authentication**: Secure login with AWS Cognito User Pool
- **Chat Interface**: Interactive chat with the deployed agent
- **Session Management**: Maintains conversation history across messages
- **Memory Integration**: Agent remembers user preferences and facts
- **Streaming Responses**: Real-time streaming of agent responses

## Prerequisites

- Python 3.8 or higher
- AWS credentials configured (for AgentCore Runtime API calls)
- Deployed AgentCore agent (CustomerAssistantAgent)

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Ensure configuration files exist in the parent directory:
   - `cognito_config.json` - Cognito User Pool configuration
   - `streamlit_user_credentials.json` - Test user credentials
   - `AgentCoreProject/agentcore/.cli/deployed-state.json` - Deployed agent ARN

## Running the Application

From the `streamlit-ui` directory:

```bash
streamlit run streamlit_app.py
```

Or from the project root:

```bash
streamlit run streamlit-ui/streamlit_app.py
```

The app will open in your browser at `http://localhost:8501`

## Default Login Credentials

For workshop convenience, the login form is pre-filled with:
- **Email**: administrator@example.com
- **Password**: Workshop1!

## How It Works

### Authentication Flow

1. User enters email and password
2. App authenticates with Cognito using `USER_PASSWORD_AUTH` flow
3. If first-time login, handles `NEW_PASSWORD_REQUIRED` challenge
4. Stores authentication tokens in Streamlit session state
5. Shows logout button in sidebar when authenticated

### Chat Flow

1. User types a message in the chat input
2. App invokes the AgentCore Runtime API with:
   - Runtime ARN from deployed state
   - Session ID (consistent per user session)
   - Actor ID (username from email)
   - User's prompt
3. Agent response streams back in real-time
4. Chat history is maintained in session state
5. Agent's memory persists across messages using session ID

### Session Management

- **Session ID**: Generated once per user session (UUID)
- **Actor ID**: Extracted from email (part before @)
- **Memory**: Agent remembers preferences, facts, and conversation history

## UI Components

### Login Page
- Email and password input fields (pre-filled for convenience)
- Login button
- Error messages for authentication failures
- New password form for first-time login

### Chat Page
- **Sidebar**: User info, session ID, logout button
- **Chat History**: All messages in the conversation
- **Chat Input**: Text box for user messages
- **Streaming Response**: Real-time agent responses with cursor

### Welcome Message
When chat starts, the agent greets with:
> "Hello! I'm your Returns & Refunds Assistant. I can help you look up orders, check return eligibility, calculate refunds and answer policy questions. How can I help you today?"

## Configuration

The app reads configuration from:

1. **Cognito Config** (`cognito_config.json`):
   - User Pool ID
   - Client ID
   - Region

2. **User Credentials** (`streamlit_user_credentials.json`):
   - Default email
   - Default password

3. **Deployed State** (`AgentCoreProject/agentcore/.cli/deployed-state.json`):
   - Runtime ARN
   - Endpoint name (DEFAULT)

## Error Handling

- Authentication failures show error messages
- Agent invocation errors are displayed in chat
- Connection timeouts are handled gracefully
- Invalid responses are caught and reported

## Security Notes

⚠️ **Workshop Configuration**:
- Login form is pre-filled for convenience
- This is suitable for workshop/demo purposes only

🔒 **Production Recommendations**:
- Remove default credentials from the form
- Implement token refresh logic
- Add session timeout
- Enable MFA for Cognito users
- Use HTTPS for production deployment
- Store sensitive config in AWS Secrets Manager

## Troubleshooting

### "Authentication error"
- Check that Cognito User Pool ID and Client ID are correct
- Verify user exists in Cognito User Pool
- Ensure password meets Cognito password policy

### "Error invoking agent"
- Verify agent is deployed: `cd AgentCoreProject && agentcore status`
- Check AWS credentials are configured
- Ensure Runtime ARN is correct in deployed-state.json
- Check CloudWatch logs for agent errors

### "Module not found"
- Install dependencies: `pip install -r requirements.txt`

### Chat not streaming
- Check network connectivity to AWS
- Verify AgentCore Runtime endpoint is accessible
- Check agent logs for errors

## Development

To modify the app:

1. **Change authentication**: Edit `authenticate_user()` function
2. **Customize UI**: Modify `chat_page()` and `login_page()` functions
3. **Add features**: Extend session state and add new components
4. **Change agent invocation**: Edit `invoke_agent()` function

## AWS Services Used

- **Amazon Cognito**: User authentication
- **AWS Bedrock AgentCore Runtime**: Agent invocation
- **AWS IAM**: Credentials for API calls

## Related Files

- `create_cognito_user.py` - Script to create test users
- `cognito_config.json` - Cognito configuration
- `streamlit_user_credentials.json` - Test user credentials
- `AgentCoreProject/agentcore/.cli/deployed-state.json` - Deployed agent info
