import logging
import os
import sys
import time
import requests
from datetime import datetime
from strands import Agent
from strands_tools import current_time
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig, RetrievalConfig
from model.load import load_model

_log_handlers = [logging.StreamHandler(sys.stderr)]
try:
    _log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent.log")
    _log_handlers.append(logging.FileHandler(_log_file, mode="a"))
except OSError:
    pass  # read-only filesystem (deployed runtime)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    handlers=_log_handlers,
    force=True,
)

app = BedrockAgentCoreApp()
log = logging.getLogger(__name__)

# Memory configuration
MEMORY_ID = os.environ.get("MEMORY_ID")
AWS_REGION = os.environ.get("AWS_REGION", "us-west-2")
DEFAULT_ACTOR_ID = "default-user"  # Match what AgentCore CLI uses

# Gateway OAuth configuration
GATEWAY_URL = os.environ.get("GATEWAY_URL")
GATEWAY_CLIENT_ID = os.environ.get("GATEWAY_CLIENT_ID")
GATEWAY_CLIENT_SECRET = os.environ.get("GATEWAY_CLIENT_SECRET")
GATEWAY_TOKEN_ENDPOINT = os.environ.get("GATEWAY_TOKEN_ENDPOINT")
GATEWAY_SCOPE = os.environ.get("GATEWAY_SCOPE")

# Token cache
_token_cache = {
    "access_token": None,
    "expires_at": 0
}


def get_gateway_access_token():
    """Get or refresh the gateway access token."""
    # Check if we have a valid cached token
    if _token_cache["access_token"] and time.time() < _token_cache["expires_at"] - 60:
        log.debug("Using cached gateway access token")
        return _token_cache["access_token"]
    
    # Get new token
    log.info("Obtaining new gateway access token from %s", GATEWAY_TOKEN_ENDPOINT)
    
    try:
        response = requests.post(
            GATEWAY_TOKEN_ENDPOINT,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data={
                'grant_type': 'client_credentials',
                'client_id': GATEWAY_CLIENT_ID,
                'client_secret': GATEWAY_CLIENT_SECRET,
                'scope': GATEWAY_SCOPE
            },
            timeout=10
        )
        response.raise_for_status()
        
        token_data = response.json()
        access_token = token_data['access_token']
        expires_in = token_data.get('expires_in', 3600)
        
        # Cache the token
        _token_cache["access_token"] = access_token
        _token_cache["expires_at"] = time.time() + expires_in
        
        log.info("Gateway access token obtained, expires in %d seconds", expires_in)
        return access_token
        
    except Exception as e:
        log.error("Failed to obtain gateway access token: %s", e)
        raise


def create_gateway_mcp_client():
    """Create an MCP client for the AgentCore Gateway."""
    if not GATEWAY_URL:
        log.warning("GATEWAY_URL not set - gateway tools will not be available")
        return None
    
    def create_transport(headers=None):
        """Create streamable HTTP transport with OAuth token."""
        access_token = get_gateway_access_token()
        auth_headers = {**headers} if headers else {}
        auth_headers["Authorization"] = f"Bearer {access_token}"
        
        log.debug("Creating gateway transport to %s", GATEWAY_URL)
        return streamablehttp_client(GATEWAY_URL, headers=auth_headers)
    
    return MCPClient(create_transport)


SYSTEM_PROMPT = """
You are a Returns & Refunds Assistant helping administrators manage customer returns and refunds.

Your role:
- Assist administrators who have access to customer data, orders, and return policies
- Help check return eligibility for customer orders
- Calculate refund amounts based on return policies
- Answer questions about return policies on behalf of customers
- Remember customer preferences, facts, and conversation history across sessions

Guidelines:
- Be helpful and concise in your responses
- Always confirm details before processing any return or refund
- Use available tools to access customer data and order information when needed
- Clearly explain return eligibility criteria and refund calculations
- Remember and use customer preferences you learn during conversations
"""

def get_or_create_agent(actor_id: str = DEFAULT_ACTOR_ID, session_id: str = None):
    """Create an agent with memory configured for the given actor and session."""
    if not session_id:
        session_id = f"session_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    log.info("Creating agent: actor_id=%s, session_id=%s, MEMORY_ID=%s", actor_id, session_id, MEMORY_ID)

    # Configure memory session manager
    session_manager = None
    if MEMORY_ID:
        retrieval_config = {
            "/facts/{actorId}/": RetrievalConfig(top_k=10, relevance_score=0.3),
            "/summaries/{actorId}/{sessionId}/": RetrievalConfig(top_k=5, relevance_score=0.3),
            "/preferences/{actorId}/": RetrievalConfig(top_k=5, relevance_score=0.3),
            "/episodes/{actorId}/{sessionId}/": RetrievalConfig(top_k=10, relevance_score=0.3),
            "/episodes/{actorId}/": RetrievalConfig(top_k=5, relevance_score=0.3),
        }

        agentcore_memory_config = AgentCoreMemoryConfig(
            memory_id=MEMORY_ID,
            session_id=session_id,
            actor_id=actor_id,
            retrieval_config=retrieval_config,
        )

        session_manager = AgentCoreMemorySessionManager(
            agentcore_memory_config=agentcore_memory_config,
            region_name=AWS_REGION,
        )
        log.info("Memory session manager created with %d retrieval namespaces", len(retrieval_config))
    else:
        log.warning("MEMORY_ID not set - memory will not be enabled")

    # Build tools list
    tools = [current_time]  # Always include current_time
    
    # Add gateway MCP client if configured
    gateway_client = create_gateway_mcp_client()
    if gateway_client:
        log.info("Adding gateway MCP client to tools")
        tools.append(gateway_client)
    else:
        log.warning("Gateway MCP client not configured - gateway tools will not be available")

    agent = Agent(
        model=load_model(),
        system_prompt=SYSTEM_PROMPT,
        tools=tools,
        session_manager=session_manager,
    )
    return agent


@app.entrypoint
async def invoke(payload, context):
    actor_id = payload.get("userId") or payload.get("actor_id") or DEFAULT_ACTOR_ID
    session_id = payload.get("sessionId") or payload.get("session_id")

    log.info("Invoke called: actor_id=%s, session_id=%s, prompt=%s",
             actor_id, session_id, (payload.get("prompt") or "")[:80])

    agent = get_or_create_agent(actor_id=actor_id, session_id=session_id)

    stream = agent.stream_async(payload.get("prompt"))

    async for event in stream:
        if "data" in event and isinstance(event["data"], str):
            yield event["data"]


if __name__ == "__main__":
    app.run()
