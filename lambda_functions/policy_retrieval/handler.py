"""
Lambda function for retrieving return policies from Bedrock Knowledge Base.
Reads Knowledge Base ID from SSM and uses Bedrock Agent Runtime retrieve API.
"""
import json
import boto3
from typing import Dict, Any, List

# Initialize AWS clients
ssm = boto3.client('ssm', region_name='us-west-2')
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name='us-west-2')

# SSM parameter for Knowledge Base ID
KB_ID_PARAMETER = '/app/workshop/kb/knowledge-base-id'

# Cache for Knowledge Base ID
_kb_id_cache = None


def get_knowledge_base_id() -> str:
    """
    Retrieve Knowledge Base ID from SSM Parameter Store.
    Caches the value for subsequent invocations.
    
    Returns:
        Knowledge Base ID string
    """
    global _kb_id_cache
    
    if _kb_id_cache is None:
        response = ssm.get_parameter(Name=KB_ID_PARAMETER)
        _kb_id_cache = response['Parameter']['Value']
    
    return _kb_id_cache


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for policy retrieval operations.
    
    Args:
        event: Input parameters from the tool invocation
        context: Lambda context with bedrockAgentCoreToolName
    
    Returns:
        Dict with the policy retrieval results
    """
    try:
        # Extract tool name from context or event (for testing)
        tool_name = None
        
        # Try to get from event first (for direct testing)
        if 'tool_name' in event:
            tool_name = event['tool_name']
        # Otherwise get from context (AgentCore Gateway invocation)
        elif hasattr(context, 'client_context') and context.client_context and hasattr(context.client_context, 'custom'):
            delimiter = "___"
            original_tool_name = context.client_context.custom['bedrockAgentCoreToolName']
            tool_name = original_tool_name[original_tool_name.index(delimiter) + len(delimiter):]
        
        # Default to policy_retrieval if query is present
        if not tool_name and 'query' in event:
            tool_name = 'policy_retrieval'
        
        # Route to appropriate handler based on tool name
        if tool_name == 'policy_retrieval':
            return handle_policy_retrieval(event)
        else:
            return {
                'error': f'Unknown or missing tool name',
                'available_tools': ['policy_retrieval'],
                'hint': 'Include "tool_name" in event for direct testing'
            }
    
    except Exception as e:
        return {
            'error': f'Error processing request: {str(e)}'
        }


def handle_policy_retrieval(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieve return policy information from Bedrock Knowledge Base.
    
    Args:
        event: Contains 'query' - the policy query text
    
    Returns:
        Dict with policy information from the knowledge base
    """
    query = event.get('query')
    
    if not query:
        return {'error': 'query parameter is required'}
    
    try:
        # Get Knowledge Base ID from SSM
        kb_id = get_knowledge_base_id()
        
        # Query the Knowledge Base using retrieve API
        response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={
                'text': query
            },
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': 5
                }
            }
        )
        
        # Extract and format results
        retrieval_results = response.get('retrievalResults', [])
        
        if not retrieval_results:
            return {
                'found': False,
                'message': f'No policy information found for query: {query}',
                'query': query
            }
        
        # Format the results
        policies = []
        for result in retrieval_results:
            content = result.get('content', {}).get('text', '')
            score = result.get('score', 0.0)
            location = result.get('location', {})
            
            policies.append({
                'content': content,
                'relevance_score': score,
                'source': location.get('s3Location', {}).get('uri', 'Unknown')
            })
        
        return {
            'found': True,
            'query': query,
            'count': len(policies),
            'policies': policies
        }
    
    except bedrock_agent_runtime.exceptions.ResourceNotFoundException:
        return {
            'error': 'Knowledge Base not found',
            'kb_id': kb_id if 'kb_id' in locals() else 'Unknown'
        }
    except Exception as e:
        return {
            'error': f'Error retrieving policy: {str(e)}',
            'query': query
        }


def format_policy_text(policies: List[Dict[str, Any]]) -> str:
    """
    Format policy results into readable text.
    
    Args:
        policies: List of policy dictionaries
    
    Returns:
        Formatted policy text
    """
    if not policies:
        return "No policies found."
    
    formatted = []
    for i, policy in enumerate(policies, 1):
        formatted.append(f"Policy {i} (Relevance: {policy['relevance_score']:.2f}):")
        formatted.append(policy['content'])
        formatted.append(f"Source: {policy['source']}")
        formatted.append("")
    
    return "\n".join(formatted)
