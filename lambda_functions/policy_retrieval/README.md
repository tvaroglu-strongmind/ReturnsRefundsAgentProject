# Policy Retrieval Lambda Function

This Lambda function retrieves return policy information from a Bedrock Knowledge Base using the Agent Runtime retrieve API.

## Tool

### policy_retrieval
Retrieve return policy information based on a natural language query.

**Input:**
- `query` (required): Natural language query about return policies (e.g., "electronics return policy in US")

**Output:**
- List of relevant policy excerpts with relevance scores
- Source document information

## Configuration

The function reads the Knowledge Base ID from SSM Parameter Store:
- **Parameter Name:** `/app/workshop/kb/knowledge-base-id`
- **Region:** us-west-2

The Knowledge Base ID is cached after the first retrieval for performance.

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
     --function-name policy-retrieval \
     --runtime python3.12 \
     --role <IAM_ROLE_ARN> \
     --handler handler.lambda_handler \
     --zip-file fileb://function.zip \
     --region us-west-2 \
     --timeout 30
   ```

## IAM Permissions Required

The Lambda execution role needs:
- `ssm:GetParameter` for reading the Knowledge Base ID
- `bedrock:Retrieve` for querying the Knowledge Base

Example policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "ssm:GetParameter",
      "Resource": "arn:aws:ssm:us-west-2:*:parameter/app/workshop/kb/knowledge-base-id"
    },
    {
      "Effect": "Allow",
      "Action": "bedrock:Retrieve",
      "Resource": "arn:aws:bedrock:us-west-2:*:knowledge-base/*"
    }
  ]
}
```

## Usage with AgentCore Gateway

Add this Lambda as a target to your AgentCore Gateway using the tool schema in `tool_schemas.json`.

The gateway will invoke the Lambda with the tool name in the context:
```python
context.client_context.custom['bedrockAgentCoreToolName']
```

## Retrieval Configuration

The function uses the following retrieval configuration:
- **Number of Results:** 5 (top 5 most relevant policy excerpts)
- **Search Type:** Vector search using embeddings

Results are sorted by relevance score (0.0 to 1.0).

## Error Handling

The function handles:
- Missing query parameter
- Knowledge Base not found
- SSM parameter not found
- Empty retrieval results

All errors are returned in a structured format with an `error` field.

## Performance Notes

- Knowledge Base ID is cached in memory across invocations
- Consider increasing Lambda timeout for complex queries (default: 30 seconds)
- Cold start time includes SSM parameter retrieval (~100-200ms)
