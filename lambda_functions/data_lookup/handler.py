"""
Lambda function for DynamoDB data lookups (orders, customers, products).
Supports three tools: order_lookup, user_lookup, and product_lookup.
"""
import json
import boto3
from typing import Dict, Any, List

# Initialize DynamoDB client
dynamodb = boto3.client('dynamodb', region_name='us-west-2')

# Table names
ORDERS_TABLE = 'workshop-orders'
CUSTOMERS_TABLE = 'workshop-customers'
PRODUCTS_TABLE = 'workshop-products'


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for data lookup operations.
    
    Args:
        event: Input parameters from the tool invocation
        context: Lambda context with bedrockAgentCoreToolName
    
    Returns:
        Dict with the lookup results
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
        
        # If no tool name specified, try to infer from event parameters
        if not tool_name:
            if 'customer_id' in event and 'product_id' not in event:
                # Could be order_lookup or user_lookup, default to order_lookup
                tool_name = 'order_lookup'
            elif 'customer_id' in event and 'product_id' in event:
                tool_name = 'order_lookup'
            elif 'product_id' in event:
                tool_name = 'product_lookup'
        
        # Route to appropriate handler based on tool name
        if tool_name == 'order_lookup':
            return handle_order_lookup(event)
        elif tool_name == 'user_lookup':
            return handle_user_lookup(event)
        elif tool_name == 'product_lookup':
            return handle_product_lookup(event)
        else:
            return {
                'error': f'Unknown or missing tool name',
                'available_tools': ['order_lookup', 'user_lookup', 'product_lookup'],
                'hint': 'Include "tool_name" in event for direct testing'
            }
    
    except Exception as e:
        return {
            'error': f'Error processing request: {str(e)}'
        }


def handle_order_lookup(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Look up orders by customer_id or by customer_id and product_id.
    
    Args:
        event: Contains 'customer_id' and optionally 'product_id'
    
    Returns:
        Dict with order details or list of orders
    """
    customer_id = event.get('customer_id')
    product_id = event.get('product_id')
    
    if not customer_id:
        return {'error': 'customer_id is required'}
    
    try:
        if product_id:
            # Query specific order
            response = dynamodb.get_item(
                TableName=ORDERS_TABLE,
                Key={
                    'customer_id': {'S': customer_id},
                    'product_id': {'S': product_id}
                }
            )
            
            if 'Item' not in response:
                return {
                    'found': False,
                    'message': f'No order found for customer {customer_id} and product {product_id}'
                }
            
            item = response['Item']
            return {
                'found': True,
                'order': {
                    'customer_id': item['customer_id']['S'],
                    'product_id': item['product_id']['S'],
                    'status': item.get('status', {}).get('S', 'UNKNOWN'),
                    'purchased_date': item.get('purchased_date', {}).get('S', 'N/A')
                }
            }
        else:
            # Query all orders for customer
            response = dynamodb.query(
                TableName=ORDERS_TABLE,
                KeyConditionExpression='customer_id = :cid',
                ExpressionAttributeValues={
                    ':cid': {'S': customer_id}
                }
            )
            
            orders = []
            for item in response.get('Items', []):
                orders.append({
                    'customer_id': item['customer_id']['S'],
                    'product_id': item['product_id']['S'],
                    'status': item.get('status', {}).get('S', 'UNKNOWN'),
                    'purchased_date': item.get('purchased_date', {}).get('S', 'N/A')
                })
            
            return {
                'found': len(orders) > 0,
                'count': len(orders),
                'orders': orders
            }
    
    except Exception as e:
        return {'error': f'Error querying orders: {str(e)}'}


def handle_user_lookup(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Look up customer information by customer_id.
    
    Args:
        event: Contains 'customer_id'
    
    Returns:
        Dict with customer details
    """
    customer_id = event.get('customer_id')
    
    if not customer_id:
        return {'error': 'customer_id is required'}
    
    try:
        response = dynamodb.get_item(
            TableName=CUSTOMERS_TABLE,
            Key={
                'customer_id': {'S': customer_id}
            }
        )
        
        if 'Item' not in response:
            return {
                'found': False,
                'message': f'Customer {customer_id} not found'
            }
        
        item = response['Item']
        return {
            'found': True,
            'customer': {
                'customer_id': item['customer_id']['S'],
                'name': item.get('name', {}).get('S', 'N/A'),
                'country_code': item.get('country_code', {}).get('S', 'N/A')
            }
        }
    
    except Exception as e:
        return {'error': f'Error querying customer: {str(e)}'}


def handle_product_lookup(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Look up product information by product_id.
    
    Args:
        event: Contains 'product_id'
    
    Returns:
        Dict with product details
    """
    product_id = event.get('product_id')
    
    if not product_id:
        return {'error': 'product_id is required'}
    
    try:
        response = dynamodb.get_item(
            TableName=PRODUCTS_TABLE,
            Key={
                'product_id': {'S': product_id}
            }
        )
        
        if 'Item' not in response:
            return {
                'found': False,
                'message': f'Product {product_id} not found'
            }
        
        item = response['Item']
        return {
            'found': True,
            'product': {
                'product_id': item['product_id']['S'],
                'product_name': item.get('product_name', {}).get('S', 'N/A'),
                'product_category': item.get('product_category', {}).get('S', 'N/A'),
                'provider': item.get('provider', {}).get('S', 'N/A')
            }
        }
    
    except Exception as e:
        return {'error': f'Error querying product: {str(e)}'}
