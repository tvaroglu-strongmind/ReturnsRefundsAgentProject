#!/usr/bin/env python3
"""
Deploy Lambda functions to AWS for AgentCore Gateway integration.
"""
import boto3
import zipfile
import os
import sys
from pathlib import Path

# AWS Configuration
REGION = 'us-west-2'
SSM_ROLE_PARAMETER = '/app/workshop/lambda/execution-role-arn'

# Initialize AWS clients
ssm = boto3.client('ssm', region_name=REGION)
lambda_client = boto3.client('lambda', region_name=REGION)


def get_execution_role_arn():
    """Get Lambda execution role ARN from SSM Parameter Store."""
    print(f"📋 Retrieving execution role ARN from SSM parameter: {SSM_ROLE_PARAMETER}")
    response = ssm.get_parameter(Name=SSM_ROLE_PARAMETER)
    role_arn = response['Parameter']['Value']
    print(f"✓ Found role: {role_arn}\n")
    return role_arn


def create_zip_package(function_dir, output_path):
    """
    Create a deployment package for a Lambda function.
    
    Args:
        function_dir: Path to the function directory
        output_path: Path for the output zip file
    """
    print(f"📦 Creating deployment package: {output_path}")
    
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add handler.py
        handler_path = os.path.join(function_dir, 'handler.py')
        if os.path.exists(handler_path):
            zipf.write(handler_path, 'handler.py')
            print(f"  ✓ Added handler.py")
        else:
            raise FileNotFoundError(f"handler.py not found in {function_dir}")
    
    print(f"✓ Package created: {os.path.getsize(output_path)} bytes\n")
    return output_path


def deploy_lambda_function(function_name, zip_path, role_arn, description, timeout=30):
    """
    Deploy or update a Lambda function.
    
    Args:
        function_name: Name of the Lambda function
        zip_path: Path to the deployment package
        role_arn: IAM role ARN for Lambda execution
        description: Function description
        timeout: Function timeout in seconds
    
    Returns:
        Lambda function ARN
    """
    print(f"🚀 Deploying Lambda function: {function_name}")
    
    # Read the zip file
    with open(zip_path, 'rb') as f:
        zip_content = f.read()
    
    try:
        # Try to update existing function
        print(f"  Checking if function exists...")
        lambda_client.get_function(FunctionName=function_name)
        
        print(f"  Function exists, updating code...")
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_content
        )
        
        # Update configuration
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Role=role_arn,
            Timeout=timeout,
            Description=description
        )
        
        print(f"✓ Function updated: {function_name}")
        
    except lambda_client.exceptions.ResourceNotFoundException:
        # Create new function
        print(f"  Function doesn't exist, creating new...")
        response = lambda_client.create_function(
            FunctionName=function_name,
            Runtime='python3.12',
            Role=role_arn,
            Handler='handler.lambda_handler',
            Code={'ZipFile': zip_content},
            Description=description,
            Timeout=timeout
        )
        print(f"✓ Function created: {function_name}")
    
    function_arn = response['FunctionArn']
    print(f"✓ Function ARN: {function_arn}\n")
    return function_arn


def main():
    """Main deployment function."""
    print("=" * 70)
    print("Lambda Function Deployment Script")
    print("=" * 70)
    print()
    
    # Get execution role ARN
    try:
        role_arn = get_execution_role_arn()
    except Exception as e:
        print(f"❌ Error retrieving execution role: {e}")
        sys.exit(1)
    
    # Define functions to deploy
    functions = [
        {
            'name': 'workshop-data-lookup',
            'dir': 'lambda_functions/data_lookup',
            'zip': 'data_lookup.zip',
            'description': 'DynamoDB data lookup for orders, customers, and products',
            'timeout': 30
        },
        {
            'name': 'workshop-policy-retrieval',
            'dir': 'lambda_functions/policy_retrieval',
            'zip': 'policy_retrieval.zip',
            'description': 'Bedrock Knowledge Base policy retrieval',
            'timeout': 30
        }
    ]
    
    deployed_functions = []
    
    # Deploy each function
    for func in functions:
        try:
            # Create deployment package
            zip_path = create_zip_package(func['dir'], func['zip'])
            
            # Deploy function
            function_arn = deploy_lambda_function(
                function_name=func['name'],
                zip_path=zip_path,
                role_arn=role_arn,
                description=func['description'],
                timeout=func['timeout']
            )
            
            deployed_functions.append({
                'name': func['name'],
                'arn': function_arn
            })
            
            # Clean up zip file
            os.remove(zip_path)
            
        except Exception as e:
            print(f"❌ Error deploying {func['name']}: {e}\n")
            continue
    
    # Print summary
    print("=" * 70)
    print("Deployment Summary")
    print("=" * 70)
    print()
    
    if deployed_functions:
        print("✓ Successfully deployed Lambda functions:\n")
        for func in deployed_functions:
            print(f"  {func['name']}")
            print(f"  ARN: {func['arn']}")
            print()
    else:
        print("❌ No functions were deployed successfully")
        sys.exit(1)
    
    print("=" * 70)
    print("Next Steps:")
    print("=" * 70)
    print("1. Add these Lambda functions as targets in your AgentCore Gateway")
    print("2. Use the tool_schemas.json files to define the tools")
    print("3. Test the tools through the gateway")
    print()


if __name__ == '__main__':
    main()
