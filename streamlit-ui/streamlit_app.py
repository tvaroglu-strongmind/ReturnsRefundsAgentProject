#!/usr/bin/env python3
"""
Streamlit Chat Application for Returns & Refunds Assistant
Integrates with AWS Cognito for authentication and AgentCore Runtime for agent invocation.
"""
import streamlit as st
import boto3
import json
import uuid
from datetime import datetime
from pathlib import Path

# AWS Configuration
AWS_REGION = "us-west-2"

# Load configuration files
CONFIG_DIR = Path(__file__).parent.parent
COGNITO_CONFIG_PATH = CONFIG_DIR / "cognito_config.json"
USER_CREDS_PATH = CONFIG_DIR / "streamlit_user_credentials.json"
DEPLOYED_STATE_PATH = CONFIG_DIR / "AgentCoreProject" / "agentcore" / ".cli" / "deployed-state.json"

# Load configurations
with open(COGNITO_CONFIG_PATH, 'r') as f:
    cognito_config = json.load(f)

with open(USER_CREDS_PATH, 'r') as f:
    user_creds = json.load(f)

with open(DEPLOYED_STATE_PATH, 'r') as f:
    deployed_state = json.load(f)

# Extract configuration values
USER_POOL_ID = cognito_config['user_pool_id']
CLIENT_ID = cognito_config['client_id']
RUNTIME_ARN = deployed_state['targets']['default']['resources']['runtimes']['CustomerAssistantAgent']['runtimeArn']
DEFAULT_EMAIL = user_creds['email']
DEFAULT_PASSWORD = user_creds['password']

# Initialize AWS clients
cognito_client = boto3.client('cognito-idp', region_name=AWS_REGION)
agentcore_client = boto3.client('bedrock-agentcore', region_name=AWS_REGION)

# Page configuration
st.set_page_config(
    page_title="Returns & Refunds Assistant",
    page_icon="🔄",
    layout="wide"
)


def authenticate_user(email: str, password: str):
    """
    Authenticate user with Cognito using USER_PASSWORD_AUTH flow.
    
    Returns:
        dict: Authentication result with tokens and user info, or None if failed
    """
    try:
        response = cognito_client.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': email,
                'PASSWORD': password
            }
        )
        
        # Check if password change is required
        if response.get('ChallengeName') == 'NEW_PASSWORD_REQUIRED':
            return {
                'challenge': 'NEW_PASSWORD_REQUIRED',
                'session': response['Session'],
                'email': email
            }
        
        # Successful authentication
        return {
            'authenticated': True,
            'id_token': response['AuthenticationResult']['IdToken'],
            'access_token': response['AuthenticationResult']['AccessToken'],
            'refresh_token': response['AuthenticationResult']['RefreshToken'],
            'email': email
        }
        
    except cognito_client.exceptions.NotAuthorizedException:
        st.error("❌ Invalid email or password")
        return None
    except Exception as e:
        st.error(f"❌ Authentication error: {str(e)}")
        return None


def handle_new_password_challenge(email: str, session: str, new_password: str):
    """
    Handle NEW_PASSWORD_REQUIRED challenge for first-time login.
    
    Returns:
        dict: Authentication result with tokens, or None if failed
    """
    try:
        response = cognito_client.respond_to_auth_challenge(
            ClientId=CLIENT_ID,
            ChallengeName='NEW_PASSWORD_REQUIRED',
            Session=session,
            ChallengeResponses={
                'USERNAME': email,
                'NEW_PASSWORD': new_password
            }
        )
        
        return {
            'authenticated': True,
            'id_token': response['AuthenticationResult']['IdToken'],
            'access_token': response['AuthenticationResult']['AccessToken'],
            'refresh_token': response['AuthenticationResult']['RefreshToken'],
            'email': email
        }
        
    except Exception as e:
        st.error(f"❌ Error setting new password: {str(e)}")
        return None


def invoke_agent(prompt: str, session_id: str, actor_id: str):
    """
    Invoke the AgentCore Runtime with streaming response.
    
    Args:
        prompt: User's message
        session_id: Session ID for conversation continuity
        actor_id: Actor ID (username)
    
    Yields:
        str: Chunks of the agent's response
    """
    try:
        response = agentcore_client.invoke_agent(
            runtimeArn=RUNTIME_ARN,
            endpointName='DEFAULT',
            inputText=prompt,
            sessionId=session_id,
            userId=actor_id,
            enableTrace=False
        )
        
        # Stream the response
        for event in response['completion']:
            if 'chunk' in event:
                chunk_data = event['chunk']
                if 'bytes' in chunk_data:
                    chunk_text = chunk_data['bytes'].decode('utf-8')
                    
                    # Try to parse as JSON first
                    try:
                        parsed = json.loads(chunk_text)
                        yield str(parsed)
                    except json.JSONDecodeError:
                        # Not JSON, yield as-is
                        yield chunk_text
                        
    except Exception as e:
        yield f"\n\n❌ Error invoking agent: {str(e)}"


def login_page():
    """Display the login page."""
    st.title("🔄 Returns & Refunds Assistant")
    st.subheader("Please log in to continue")
    
    # Check if we're in password change mode
    if 'password_challenge' in st.session_state:
        st.warning("⚠️ You need to set a new password for your first login")
        
        with st.form("new_password_form"):
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submit = st.form_submit_button("Set New Password")
            
            if submit:
                if new_password != confirm_password:
                    st.error("❌ Passwords do not match")
                elif len(new_password) < 8:
                    st.error("❌ Password must be at least 8 characters")
                else:
                    result = handle_new_password_challenge(
                        st.session_state.password_challenge['email'],
                        st.session_state.password_challenge['session'],
                        new_password
                    )
                    
                    if result and result.get('authenticated'):
                        st.session_state.auth = result
                        st.session_state.session_id = str(uuid.uuid4())
                        st.session_state.messages = []
                        del st.session_state.password_challenge
                        st.rerun()
    else:
        # Regular login form
        with st.form("login_form"):
            email = st.text_input("Email", value=DEFAULT_EMAIL)
            password = st.text_input("Password", type="password", value=DEFAULT_PASSWORD)
            submit = st.form_submit_button("Login")
            
            if submit:
                result = authenticate_user(email, password)
                
                if result:
                    if result.get('challenge') == 'NEW_PASSWORD_REQUIRED':
                        st.session_state.password_challenge = result
                        st.rerun()
                    elif result.get('authenticated'):
                        st.session_state.auth = result
                        st.session_state.session_id = str(uuid.uuid4())
                        st.session_state.messages = []
                        st.success("✅ Login successful!")
                        st.rerun()


def chat_page():
    """Display the chat interface."""
    # Sidebar
    with st.sidebar:
        st.title("🔄 Session Info")
        
        # Extract username from email
        email = st.session_state.auth['email']
        username = email.split('@')[0]
        
        st.write(f"**User:** {email}")
        st.write(f"**Actor ID:** {username}")
        st.write(f"**Session ID:** {st.session_state.session_id[:8]}...")
        
        st.divider()
        
        if st.button("🚪 Logout", use_container_width=True):
            # Clear session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    # Main chat interface
    st.title("🔄 Returns & Refunds Assistant")
    
    # Initialize messages if empty
    if not st.session_state.messages:
        welcome_message = (
            "Hello! I'm your Returns & Refunds Assistant. I can help you look up orders, "
            "check return eligibility, calculate refunds and answer policy questions. "
            "How can I help you today?"
        )
        st.session_state.messages.append({
            "role": "assistant",
            "content": welcome_message
        })
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Type your message here..."):
        # Add user message to history
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })
        
        # Display user message
        with st.chat_message("user"):
            st.write(prompt)
        
        # Get agent response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            # Extract username for actor_id
            username = st.session_state.auth['email'].split('@')[0]
            
            # Stream the response
            try:
                for chunk in invoke_agent(
                    prompt=prompt,
                    session_id=st.session_state.session_id,
                    actor_id=username
                ):
                    full_response += chunk
                    message_placeholder.write(full_response + "▌")
                
                message_placeholder.write(full_response)
                
            except Exception as e:
                error_message = f"❌ Error: {str(e)}"
                message_placeholder.write(error_message)
                full_response = error_message
        
        # Add assistant response to history
        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response
        })


def main():
    """Main application entry point."""
    # Initialize session state
    if 'auth' not in st.session_state:
        st.session_state.auth = None
    
    if 'session_id' not in st.session_state:
        st.session_state.session_id = None
    
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    # Route to appropriate page
    if st.session_state.auth and st.session_state.auth.get('authenticated'):
        chat_page()
    else:
        login_page()


if __name__ == "__main__":
    main()
