#!/usr/bin/env python3
"""
Setup Cognito User Pool for AgentCore Gateway authentication.
Creates user pool, domain, resource server, and app client for machine-to-machine auth.
"""
import boto3
import json
import time
from datetime import datetime

# Configuration
REGION = 'us-west-2'
USER_POOL_NAME = 'workshop-gateway-auth'
DOMAIN_PREFIX = f'workshop-gateway-{int(time.time())}'  # Unique domain prefix
RESOURCE_SERVER_IDENTIFIER = 'workshop-gateway'
RESOURCE_SERVER_NAME = 'Workshop Gateway API'
SCOPE_NAME = 'invoke'
SCOPE_DESCRIPTION = 'Permission to invoke gateway tools'
APP_CLIENT_NAME = 'workshop-gateway-client'

# Initialize Cognito client
cognito = boto3.client('cognito-idp', region_name=REGION)

print("=" * 70)
print("Cognito User Pool Setup for AgentCore Gateway")
print("=" * 70)
print()


def create_user_pool():
    """Create Cognito User Pool."""
    print(f"📋 Creating User Pool: {USER_POOL_NAME}")
    
    response = cognito.create_user_pool(
        PoolName=USER_POOL_NAME,
        Policies={
            'PasswordPolicy': {
                'MinimumLength': 8,
                'RequireUppercase': False,
                'RequireLowercase': False,
                'RequireNumbers': False,
                'RequireSymbols': False
            }
        },
        AutoVerifiedAttributes=[],
        Schema=[
            {
                'Name': 'email',
                'AttributeDataType': 'String',
                'Required': False,
                'Mutable': True
            }
        ]
    )
    
    user_pool_id = response['UserPool']['Id']
    print(f"✓ User Pool created: {user_pool_id}\n")
    return user_pool_id


def create_domain(user_pool_id):
    """Create Cognito domain for OAuth endpoints."""
    print(f"🌐 Creating domain: {DOMAIN_PREFIX}")
    
    try:
        cognito.create_user_pool_domain(
            Domain=DOMAIN_PREFIX,
            UserPoolId=user_pool_id
        )
        print(f"✓ Domain created: {DOMAIN_PREFIX}.auth.{REGION}.amazoncognito.com\n")
        return DOMAIN_PREFIX
    except cognito.exceptions.InvalidParameterException as e:
        if 'Domain already exists' in str(e):
            print(f"⚠️  Domain already exists, using: {DOMAIN_PREFIX}\n")
            return DOMAIN_PREFIX
        raise


def create_resource_server(user_pool_id):
    """Create resource server with custom scope."""
    print(f"🔧 Creating resource server: {RESOURCE_SERVER_IDENTIFIER}")
    
    response = cognito.create_resource_server(
        UserPoolId=user_pool_id,
        Identifier=RESOURCE_SERVER_IDENTIFIER,
        Name=RESOURCE_SERVER_NAME,
        Scopes=[
            {
                'ScopeName': SCOPE_NAME,
                'ScopeDescription': SCOPE_DESCRIPTION
            }
        ]
    )
    
    full_scope = f"{RESOURCE_SERVER_IDENTIFIER}/{SCOPE_NAME}"
    print(f"✓ Resource server created")
    print(f"  Scope: {full_scope}\n")
    return full_scope


def create_app_client(user_pool_id, full_scope):
    """Create app client for machine-to-machine authentication."""
    print(f"📱 Creating app client: {APP_CLIENT_NAME}")
    
    response = cognito.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=APP_CLIENT_NAME,
        GenerateSecret=True,
        ExplicitAuthFlows=[],  # No user auth flows for M2M
        AllowedOAuthFlows=['client_credentials'],
        AllowedOAuthScopes=[full_scope],
        AllowedOAuthFlowsUserPoolClient=True,
        PreventUserExistenceErrors='ENABLED'
    )
    
    client_id = response['UserPoolClient']['ClientId']
    print(f"✓ App client created: {client_id}\n")
    
    # Get client secret
    print("🔑 Retrieving client secret...")
    client_response = cognito.describe_user_pool_client(
        UserPoolId=user_pool_id,
        ClientId=client_id
    )
    
    client_secret = client_response['UserPoolClient']['ClientSecret']
    print(f"✓ Client secret retrieved\n")
    
    return client_id, client_secret


def save_config(user_pool_id, domain_prefix, client_id, client_secret, full_scope):
    """Save configuration to JSON file."""
    print("💾 Saving configuration to cognito_config.json")
    
    # Construct URLs
    domain = f"{domain_prefix}.auth.{REGION}.amazoncognito.com"
    token_endpoint = f"https://{domain}/oauth2/token"
    discovery_url = f"https://cognito-idp.{REGION}.amazonaws.com/{user_pool_id}/.well-known/openid-configuration"
    
    config = {
        "user_pool_id": user_pool_id,
        "region": REGION,
        "domain_prefix": domain_prefix,
        "domain": domain,
        "client_id": client_id,
        "client_secret": client_secret,
        "resource_server_identifier": RESOURCE_SERVER_IDENTIFIER,
        "scope": full_scope,
        "token_endpoint": token_endpoint,
        "discovery_url": discovery_url,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    
    with open('cognito_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✓ Configuration saved\n")
    return config


def print_summary(config):
    """Print configuration summary."""
    print("=" * 70)
    print("Configuration Summary")
    print("=" * 70)
    print()
    print(f"User Pool ID:       {config['user_pool_id']}")
    print(f"Region:             {config['region']}")
    print(f"Domain:             {config['domain']}")
    print(f"Client ID:          {config['client_id']}")
    print(f"Client Secret:      {config['client_secret'][:20]}...")
    print(f"Scope:              {config['scope']}")
    print()
    print("OAuth Endpoints:")
    print(f"  Token:            {config['token_endpoint']}")
    print(f"  Discovery:        {config['discovery_url']}")
    print()
    print("=" * 70)
    print("Testing Token Retrieval")
    print("=" * 70)
    print()
    print("To test authentication, run:")
    print()
    print(f"curl -X POST {config['token_endpoint']} \\")
    print(f"  -H 'Content-Type: application/x-www-form-urlencoded' \\")
    print(f"  -d 'grant_type=client_credentials' \\")
    print(f"  -d 'client_id={config['client_id']}' \\")
    print(f"  -d 'client_secret={config['client_secret']}' \\")
    print(f"  -d 'scope={config['scope']}'")
    print()


def main():
    """Main setup function."""
    try:
        # Create user pool
        user_pool_id = create_user_pool()
        
        # Create domain
        domain_prefix = create_domain(user_pool_id)
        
        # Create resource server with scope
        full_scope = create_resource_server(user_pool_id)
        
        # Create app client
        client_id, client_secret = create_app_client(user_pool_id, full_scope)
        
        # Save configuration
        config = save_config(user_pool_id, domain_prefix, client_id, client_secret, full_scope)
        
        # Print summary
        print_summary(config)
        
        print("=" * 70)
        print("✅ Setup Complete!")
        print("=" * 70)
        print()
        print("Configuration saved to: cognito_config.json")
        print()
        
    except Exception as e:
        print(f"\n❌ Error during setup: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
