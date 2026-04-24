# Lambda Functions for AgentCore Gateway

This directory contains Lambda functions designed to be used as targets in an Amazon Bedrock AgentCore Gateway.

## Overview

These Lambda functions provide tools for the Returns & Refunds Assistant agent:

1. **data_lookup** - Query DynamoDB tables for orders, customers, and products
2. **policy_retrieval** - Retrieve return policies from Bedrock Knowledge Base

## DynamoDB Table Structure

### workshop-customers
- **Primary Key:** `customer_id` (String, HASH)
- **Attributes:**
  - `name` (String) - Customer name
  - `country_code` (String) - Two-letter country code

### workshop-orders
- **Primary Key:** 
  - `customer_id` (String, HASH)
  - `product_id` (String, RANGE)
- **Attributes:**
  - `status` (String) - Order status (DELIVERED, SHIPPED, OPENED)
  - `purchased_date` (String) - Purchase date (YYYY-MM-DD)

### workshop-products
- **Primary Key:** `product_id` (String, HASH)
- **Attributes:**
  - `product_name` (String) - Product name
  - `product_category` (String) - Category (electronics, tablet, phone, etc.)
  - `provider` (String) - Manufacturer/provider name

## Lambda Function Format

Both Lambda functions follow the AgentCore Gateway Lambda target format:

### Event Object
Contains the input parameters from the tool's inputSchema:
```python
{
  "customer_id": "C-01",
  "product_id": "P-001"
}
```

### Context Object
Contains metadata including the tool name:
```python
context.client_context.custom['bedrockAgentCoreToolName']
# Format: "target_name___tool_name"
```

### Response Format
Returns a JSON object matching the tool's outputSchema:
```python
{
  "found": true,
  "customer": {
    "customer_id": "C-01",
    "name": "Rajesh Kumar",
    "country_code": "IN"
  }
}
```

## Deployment Steps

### 1. Package Each Function

```bash
# For data_lookup
cd lambda_functions/data_lookup
pip install -r requirements.txt -t .
zip -r ../../data_lookup.zip .
cd ../..

# For policy_retrieval
cd lambda_functions/policy_retrieval
pip install -r requirements.txt -t .
zip -r ../../policy_retrieval.zip .
cd ../..
```

### 2. Create IAM Execution Role

Create a role with the following policies:
- AWSLambdaBasicExecutionRole (managed policy)
- Custom policy for DynamoDB access (see data_lookup/README.md)
- Custom policy for Bedrock and SSM access (see policy_retrieval/README.md)

### 3. Deploy Lambda Functions

```bash
# Deploy data_lookup
aws lambda create-function \
  --function-name workshop-data-lookup \
  --runtime python3.12 \
  --role arn:aws:iam::ACCOUNT_ID:role/ROLE_NAME \
  --handler handler.lambda_handler \
  --zip-file fileb://data_lookup.zip \
  --region us-west-2 \
  --timeout 30

# Deploy policy_retrieval
aws lambda create-function \
  --function-name workshop-policy-retrieval \
  --runtime python3.12 \
  --role arn:aws:iam::ACCOUNT_ID:role/ROLE_NAME \
  --handler handler.lambda_handler \
  --zip-file fileb://policy_retrieval.zip \
  --region us-west-2 \
  --timeout 30
```

### 4. Add to AgentCore Gateway

Use the tool schemas in each function's `tool_schemas.json` file when adding the Lambda functions as targets to your AgentCore Gateway.

## Testing

### Test data_lookup locally:
```python
import json
from lambda_functions.data_lookup.handler import lambda_handler

# Mock context
class MockContext:
    class ClientContext:
        custom = {
            'bedrockAgentCoreToolName': 'data_lookup___user_lookup'
        }
    client_context = ClientContext()

event = {"customer_id": "C-01"}
result = lambda_handler(event, MockContext())
print(json.dumps(result, indent=2))
```

### Test policy_retrieval locally:
```python
import json
from lambda_functions.policy_retrieval.handler import lambda_handler

# Mock context
class MockContext:
    class ClientContext:
        custom = {
            'bedrockAgentCoreToolName': 'policy_retrieval___policy_retrieval'
        }
    client_context = ClientContext()

event = {"query": "electronics return policy"}
result = lambda_handler(event, MockContext())
print(json.dumps(result, indent=2))
```

## Tool Names

When added to AgentCore Gateway, the tools will be named:
- `{target_name}___order_lookup`
- `{target_name}___user_lookup`
- `{target_name}___product_lookup`
- `{target_name}___policy_retrieval`

The Lambda functions automatically strip the target name prefix to determine which tool was called.

## Region

All resources are configured for **us-west-2** region.

## Dependencies

Both functions use:
- `boto3>=1.28.0` - AWS SDK for Python

No additional dependencies required.
