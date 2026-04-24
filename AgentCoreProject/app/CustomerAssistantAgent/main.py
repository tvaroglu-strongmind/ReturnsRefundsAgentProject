from strands import Agent, tool
from strands_tools import current_time
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig, RetrievalConfig
from model.load import load_model
from mcp_client.client import get_streamable_http_mcp_client
from datetime import datetime, timedelta
import os

app = BedrockAgentCoreApp()
log = app.logger

# Memory configuration
MEMORY_ID = os.environ.get("MEMORY_ID")
AWS_REGION = os.environ.get("AWS_REGION", "us-west-2")
DEFAULT_ACTOR_ID = "default-user"  # Match what AgentCore CLI uses

# Define a Streamable HTTP MCP Client
mcp_clients = [get_streamable_http_mcp_client()]

# Define a collection of tools used by the model
tools = []

# Add built-in current_time tool
tools.append(current_time)

# Mock data for tools
MOCK_ORDERS = {
    "ORD-001": {
        "order_id": "ORD-001",
        "customer_id": "C-01",
        "product_id": "P-001",
        "product_name": "iPhone 15 Pro",
        "status": "DELIVERED",
        "purchase_date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
    },
    "ORD-002": {
        "order_id": "ORD-002",
        "customer_id": "C-02",
        "product_id": "P-003",
        "product_name": "Kindle Paperwhite",
        "status": "DELIVERED",
        "purchase_date": (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d"),
    },
    "ORD-003": {
        "order_id": "ORD-003",
        "customer_id": "C-01",
        "product_id": "P-005",
        "product_name": "PlayStation 5",
        "status": "SHIPPED",
        "purchase_date": datetime.now().strftime("%Y-%m-%d"),
    },
}

MOCK_USERS = {
    "C-01": {
        "user_id": "C-01",
        "name": "Rajesh Kumar",
        "country": "IN",
        "email": "rajesh@example.com",
    },
    "C-02": {
        "user_id": "C-02",
        "name": "Sarah Johnson",
        "country": "US",
        "email": "sarah@example.com",
    },
    "C-03": {
        "user_id": "C-03",
        "name": "James Wilson",
        "country": "UK",
        "email": "james@example.com",
    },
}

MOCK_PRODUCTS = {
    "P-001": {
        "product_id": "P-001",
        "name": "iPhone 15 Pro",
        "brand": "Apple",
        "category": "phone",
    },
    "P-002": {
        "product_id": "P-002",
        "name": "Kindle Paperwhite",
        "brand": "Amazon",
        "category": "e-book",
    },
    "P-003": {
        "product_id": "P-003",
        "name": "iPad Air",
        "brand": "Apple",
        "category": "tablet",
    },
}

MOCK_POLICIES = {
    "electronics": {
        "category": "electronics",
        "return_window_days": 30,
        "refund_percentage": 100,
        "conditions": "100% refund if unopened, otherwise subject to inspection",
    },
    "clothing": {
        "category": "clothing",
        "return_window_days": 60,
        "refund_percentage": 100,
        "conditions": "Full refund with tags attached and unworn",
    },
    "books": {
        "category": "books",
        "return_window_days": 14,
        "refund_percentage": 50,
        "conditions": "50% refund on all book returns",
    },
}

@tool
def order_lookup(order_id: str) -> str:
    """Look up order details by order ID"""
    order = MOCK_ORDERS.get(order_id)
    if not order:
        return f"Order {order_id} not found"
    
    return f"""Order Details:
- Order ID: {order['order_id']}
- Customer ID: {order['customer_id']}
- Product ID: {order['product_id']}
- Product Name: {order['product_name']}
- Status: {order['status']}
- Purchase Date: {order['purchase_date']}"""

tools.append(order_lookup)

@tool
def user_lookup(user_id: str) -> str:
    """Retrieve customer information by user ID"""
    user = MOCK_USERS.get(user_id)
    if not user:
        return f"User {user_id} not found"
    
    return f"""Customer Details:
- User ID: {user['user_id']}
- Name: {user['name']}
- Country: {user['country']}
- Email: {user['email']}"""

tools.append(user_lookup)

@tool
def product_lookup(product_id: str) -> str:
    """Retrieve product information by product ID"""
    product = MOCK_PRODUCTS.get(product_id)
    if not product:
        return f"Product {product_id} not found"
    
    return f"""Product Details:
- Product ID: {product['product_id']}
- Name: {product['name']}
- Brand: {product['brand']}
- Category: {product['category']}"""

tools.append(product_lookup)

@tool
def policy_retrieval(query: str) -> str:
    """Retrieve return policy information based on query"""
    query_lower = query.lower()
    
    # Simple keyword matching for categories
    for category, policy in MOCK_POLICIES.items():
        if category in query_lower:
            return f"""Return Policy for {policy['category'].title()}:
- Return Window: {policy['return_window_days']} days
- Refund Percentage: {policy['refund_percentage']}%
- Conditions: {policy['conditions']}"""
    
    # Return all policies if no specific match
    all_policies = "\n\n".join([
        f"{policy['category'].title()}: {policy['return_window_days']} days, {policy['refund_percentage']}% refund - {policy['conditions']}"
        for policy in MOCK_POLICIES.values()
    ])
    return f"Available Return Policies:\n\n{all_policies}"

tools.append(policy_retrieval)


# Add MCP client to tools if available
for mcp_client in mcp_clients:
    if mcp_client:
        tools.append(mcp_client)

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
    """
    Create an agent with memory configured for the given actor and session.
    Each session gets a fresh agent instance to ensure proper memory isolation.
    """
    # Generate session_id if not provided
    if not session_id:
        session_id = f"session_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    log.info(f"Creating agent with actor_id={actor_id}, session_id={session_id}")
    
    # Configure memory session manager with retrieval config
    session_manager = None
    if MEMORY_ID:
        log.info(f"Configuring memory: MEMORY_ID={MEMORY_ID}, AWS_REGION={AWS_REGION}")
        
        # Configure retrieval config with namespace patterns matching agentcore.json
        retrieval_config = {
            "/facts/{actorId}/": RetrievalConfig(top_k=10, relevance_score=0.7),
            "/summaries/{actorId}/{sessionId}/": RetrievalConfig(top_k=5, relevance_score=0.5),
            "/preferences/{actorId}/": RetrievalConfig(top_k=5, relevance_score=0.7),
            "/episodes/{actorId}/{sessionId}/": RetrievalConfig(top_k=10, relevance_score=0.6),
            "/episodes/{actorId}/": RetrievalConfig(top_k=5, relevance_score=0.6)
        }
        
        log.info(f"Retrieval namespaces: {list(retrieval_config.keys())}")
        
        # Configure memory
        agentcore_memory_config = AgentCoreMemoryConfig(
            memory_id=MEMORY_ID,
            session_id=session_id,
            actor_id=actor_id,
            retrieval_config=retrieval_config
        )
        
        # Create session manager
        session_manager = AgentCoreMemorySessionManager(
            agentcore_memory_config=agentcore_memory_config,
            region_name=AWS_REGION
        )
        log.info("Memory session manager created successfully")
    else:
        log.warning("MEMORY_ID not set - memory will not be enabled")
    
    # Create new agent for this session
    agent = Agent(
        model=load_model(),
        system_prompt=SYSTEM_PROMPT,
        tools=tools,
        session_manager=session_manager
    )
    
    log.info(f"Agent created for session_id={session_id}")
    return agent


@app.entrypoint
async def invoke(payload, context):
    log.info("=== INVOKE CALLED ===")
    log.info(f"Payload keys: {list(payload.keys())}")

    # AgentCore CLI sends "userId" not "actor_id"
    # Try both for compatibility
    actor_id = payload.get("userId") or payload.get("actor_id") or DEFAULT_ACTOR_ID
    session_id = payload.get("sessionId") or payload.get("session_id")
    
    log.info(f"Configuration: actor_id={actor_id}, session_id={session_id}")
    log.info(f"Environment: MEMORY_ID={MEMORY_ID}, AWS_REGION={AWS_REGION}")
    
    agent = get_or_create_agent(actor_id=actor_id, session_id=session_id)

    # Execute and format response
    stream = agent.stream_async(payload.get("prompt"))

    async for event in stream:
        # Handle Text parts of the response
        if "data" in event and isinstance(event["data"], str):
            yield event["data"]


if __name__ == "__main__":
    app.run()
