# Data Lookup Lambda Function

This Lambda function provides three tools for looking up data from DynamoDB tables in the workshop environment.

## Tools

### 1. order_lookup
Look up order information by customer ID and optionally product ID.

**Input:**
- `customer_id` (required): Customer ID (e.g., "C-01")
- `product_id` (optional): Product ID for specific order lookup (e.g., "P-001")

**Output:**
- Single order details if product_id provided
- List of all orders if only customer_id provided

### 2. user_lookup
Look up customer information by customer ID.

**Input:**
- `customer_id` (required): Customer ID (e.g., "C-01")

**Output:**
- Customer details including name and country code

### 3. product_lookup
Look up product information by product ID.

**Input:**
- `product_id` (required): Product ID (e.g., "P-001")

**Output:**
- Product details including name, category, and provider

## DynamoDB Tables

### workshop-customers
- **Primary Key:** customer_id (String)
- **Attributes:** name, country_code

### workshop-orders
- **Primary Key:** customer_id (Hash), product_id (Range)
- **Attributes:** status, purchased_date

### workshop-products
- **Primary Key:** product_id (String)
- **Attributes:** product_name, product_category, provider

## Deployment

1. Install dependencies:
   ```bash
   pip install -r requirements.txt -t .
   ```

2. Create deployment package:
   ```bash
   zip -r function.zip .
   ```

3. Deploy to Lambda:
   ```bash
   aws lambda create-function \
     --function-name data-lookup \
     --runtime python3.12 \
     --role <IAM_ROLE_ARN> \
     --handler handler.lambda_handler \
     --zip-file fileb://function.zip \
     --region us-west-2
   ```

## IAM Permissions Required

The Lambda execution role needs:
- `dynamodb:GetItem` on workshop-customers and workshop-products
- `dynamodb:Query` and `dynamodb:GetItem` on workshop-orders

Example policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:Query"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-west-2:*:table/workshop-customers",
        "arn:aws:dynamodb:us-west-2:*:table/workshop-orders",
        "arn:aws:dynamodb:us-west-2:*:table/workshop-products"
      ]
    }
  ]
}
```

## Usage with AgentCore Gateway

Add this Lambda as a target to your AgentCore Gateway using the tool schemas in `tool_schemas.json`.

The gateway will invoke the Lambda with the tool name in the context:
```python
context.client_context.custom['bedrockAgentCoreToolName']
```

The function automatically routes to the appropriate handler based on the tool name.
