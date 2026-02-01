import os
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from dotenv import load_dotenv

def load_config():
    """
    Load environment variables from .env file.
    Searches in current directory and sibling 'mcp' directory.
    """
    # Check current directory
    if os.path.exists('.env'):
        load_dotenv('.env')
        return
    else:
        # Fallback: look for .env in current directory absolute path
        # This handles cases where CWD might be different
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        if os.path.exists(env_path):
            load_dotenv(env_path)

def get_opensearch_client(url=None, region=None):
    """
    Initialize and return an OpenSearch client.
    
    Args:
        url (str): OpenSearch endpoint URL. If None, tries to read OPENSEARCH_URL from env.
        region (str): AWS region. If None, tries to read AWS_REGION from env (defaults to us-east-1).

    Returns:
        OpenSearch: A configured OpenSearch client, or None if configuration is missing.
    """
    # Load config if not already loaded (or ensuring env vars are present)
    load_config()

    if not url:
        url = os.getenv('OPENSEARCH_URL')

    if not region:
        region = os.getenv('AWS_REGION', 'us-east-1')

    if not url or url.strip() == "" or url == "https://":
        # Can't connect without a URL
        return None

    # Clean the host URL
    host = url.replace('https://', '').replace('http://', '').split('/')[0]
    
    # Detect service: 'aoss' for serverless, 'es' for standard
    service = 'aoss' if 'aoss' in host else 'es'
    
    try:
        credentials = boto3.Session().get_credentials()
        auth = AWSV4SignerAuth(credentials, region, service)
        
        client = OpenSearch(
            hosts=[{'host': host, 'port': 443}],
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection
        )
        return client
    except Exception as e:
        print(f"Error initializing OpenSearch client: {e}")
        return None
