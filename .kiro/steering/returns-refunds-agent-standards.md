---
inclusion: auto
---

# Returns & Refunds Agent - Development Standards

This steering document ensures consistent, high-quality development for the Returns & Refunds assistant built with Strands Agents SDK and AWS Bedrock AgentCore.

## Core Principles

### Documentation-First Approach
- **ALWAYS search AWS and Strands documentation using MCP tools before writing code**
- Never rely solely on your own knowledge - documentation changes frequently
- Use `mcp_awslabsaws_documentation_mcp_server_search_documentation` for AWS docs
- Use `mcp_strands_agents_search_docs` and `mcp_strands_agents_fetch_doc` for Strands docs
- Verify API signatures, parameters, and patterns from official sources

### AWS Best Practices
- Follow AWS Well-Architected Framework principles
- All AWS operations target the **us-west-2** region
- Use IAM roles with least privilege access
- Implement proper error handling for AWS service calls
- Always include `--no-cli-pager` when running AWS CLI commands from terminal

### Python Code Standards
- Use type hints for all function signatures and variables
- Include educational inline comments explaining:
  - Why specific approaches are used
  - How AWS/Strands patterns work
  - Important configuration choices
- Keep code minimal and focused on core concepts
- Follow PEP 8 style guidelines

### Strands Agents SDK Patterns
- Use the `@tool` decorator pattern for all agent tools
- Structure agents with clear separation of concerns
- Implement proper conversation state management
- Follow Strands best practices for:
  - Tool definitions and schemas
  - Agent initialization and configuration
  - Model provider setup
  - Error handling and logging

### AgentCore CLI Integration
- Use AgentCore CLI for local development and testing
- Follow AgentCore deployment patterns
- Implement proper agent configuration files
- Test locally before deploying to Bedrock

## Project-Specific Guidelines

### Returns & Refunds Domain
- Focus on customer service automation
- Handle common scenarios: order lookup, return eligibility, refund processing
- Implement clear user feedback and confirmation flows
- Maintain conversation context across multi-turn interactions

### Code Organization
- Keep agent logic modular and testable
- Separate tool implementations from agent configuration
- Use clear naming conventions for tools and functions
- Document expected inputs and outputs

### Development Workflow
1. Search documentation for relevant patterns
2. Write minimal, focused code with type hints
3. Add educational comments
4. Test locally with AgentCore CLI
5. Validate against AWS best practices

## Example Code Pattern

```python
from typing import Dict, Any
from strands import Agent, tool

@tool
def check_return_eligibility(order_id: str) -> Dict[str, Any]:
    """
    Check if an order is eligible for return.
    
    Uses the @tool decorator to expose this function to the agent.
    The agent can call this tool when customers ask about returns.
    
    Args:
        order_id: The unique identifier for the customer's order
        
    Returns:
        Dictionary containing eligibility status and reason
    """
    # Implementation here
    pass
```

## Reminders
- Search docs BEFORE writing code
- Use type hints ALWAYS
- Add educational comments
- Target us-west-2 region
- Include --no-cli-pager in CLI commands
- Keep code minimal and focused
