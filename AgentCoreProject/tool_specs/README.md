# AgentCore Gateway Tool Specifications

This directory contains tool specification JSON files for integrating Lambda functions with Amazon Bedrock AgentCore Gateway.

## Files

### data_lookup.json
Tool specifications for the `workshop-data-lookup` Lambda function.

**Lambda ARN:** `arn:aws:lambda:us-west-2:369069562603:function:workshop-data-lookup`

**Tools:**
- `order_lookup` - Query orders by customer_id (and optionally product_id)
- `user_lookup` - Get customer details by customer_id
- `product_lookup` - Get product details by product_id

### policy_retrieval.json
Tool specification for the `workshop-policy-retrieval` Lambda function.

**Lambda ARN:** `arn:aws:lambda:us-west-2:369069562603:function:workshop-policy-retrieval`

**Tools:**
- `policy_retrieval` - Query Bedrock Knowledge Base for return policies

## Tool Specification Format

Each tool specification follows the AgentCore Gateway Lambda tool format:

```json
{
  "name": "tool_name",
  "description": "Tool description for the LLM",
  "inputSchema": {
    "type": "object",
    "description": "Schema description",
    "properties": {
      "param_name": {
        "type": "string|number|boolean|array|object",
        "description": "Parameter description"
      }
    },
    "required": ["param_name"]
  }
}
```

**Note:** `outputSchema` is optional and not included in these specifications.

## Adding Tools to AgentCore Gateway

### Option 1: Using AWS CLI

```bash
# Create gateway target for data lookup
aws bedrock-agentcore create-gateway-target \
  --gateway-id <GATEWAY_ID> \
  --target-name data-lookup \
  --target-type LAMBDA \
  --lambda-configuration '{
    "lambdaArn": "arn:aws:lambda:us-west-2:369069562603:function:workshop-data-lookup",
    "toolDefinitions": <PASTE_data_lookup.json_CONTENT>
  }' \
  --region us-west-2

# Create gateway target for policy retrieval
aws bedrock-agentcore create-gateway-target \
  --gateway-id <GATEWAY_ID> \
  --target-name policy-retrieval \
  --target-type LAMBDA \
  --lambda-configuration '{
    "lambdaArn": "arn:aws:lambda:us-west-2:369069562603:function:workshop-policy-retrieval",
    "toolDefinitions": <PASTE_policy_retrieval.json_CONTENT>
  }' \
  --region us-west-2
```

### Option 2: Using AWS Console

1. Navigate to Amazon Bedrock AgentCore Gateway
2. Select your gateway
3. Click "Add target"
4. Choose "Lambda function" as target type
5. Enter target name (e.g., "data-lookup")
6. Select the Lambda function ARN
7. Paste the tool specification JSON from the appropriate file
8. Save the target

### Option 3: Upload to S3

You can upload these JSON files to S3 and reference them when creating the gateway target:

```bash
# Upload to S3
aws s3 cp data_lookup.json s3://your-bucket/tool-specs/data_lookup.json
aws s3 cp policy_retrieval.json s3://your-bucket/tool-specs/policy_retrieval.json

# Reference in gateway target creation
aws bedrock-agentcore create-gateway-target \
  --gateway-id <GATEWAY_ID> \
  --target-name data-lookup \
  --target-type LAMBDA \
  --lambda-configuration '{
    "lambdaArn": "arn:aws:lambda:us-west-2:369069562603:function:workshop-data-lookup",
    "toolDefinitionsS3Location": {
      "s3Uri": "s3://your-bucket/tool-specs/data_lookup.json"
    }
  }' \
  --region us-west-2
```

## Tool Naming Convention

When added to the gateway, tools will be prefixed with the target name:

- `data-lookup___order_lookup`
- `data-lookup___user_lookup`
- `data-lookup___product_lookup`
- `policy-retrieval___policy_retrieval`

The Lambda functions automatically strip this prefix to determine which tool was called.

## Testing Tools Through Gateway

Once added to the gateway, you can test the tools using the gateway's MCP protocol:

```bash
# List available tools
aws bedrock-agentcore-runtime list-tools \
  --gateway-id <GATEWAY_ID> \
  --region us-west-2

# Invoke a tool
aws bedrock-agentcore-runtime invoke-tool \
  --gateway-id <GATEWAY_ID> \
  --tool-name "data-lookup___order_lookup" \
  --tool-input '{"customer_id": "C-01"}' \
  --region us-west-2
```

## IAM Permissions

The gateway needs permission to invoke the Lambda functions. Add this policy to the gateway's execution role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": [
        "arn:aws:lambda:us-west-2:369069562603:function:workshop-data-lookup",
        "arn:aws:lambda:us-west-2:369069562603:function:workshop-policy-retrieval"
      ]
    }
  ]
}
```

## Validation

To validate the JSON format:

```bash
# Validate JSON syntax
python3 -m json.tool data_lookup.json
python3 -m json.tool policy_retrieval.json
```

Both files should parse without errors.

## References

- [AWS Documentation: Lambda function targets](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-add-target-lambda.html)
- [AWS Documentation: AgentCore Gateway](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-using.html)
- [Lambda Function Deployment Summary](../../lambda_functions/DEPLOYMENT_SUMMARY.md)
