import os
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from dotenv import load_dotenv
from utils import get_opensearch_client

def main():
    # 1. Initialize Client
    print("🔄 Connecting to OpenSearch...")
    client = get_opensearch_client()
    
    if not client:
        print("❌ Failed to connect to OpenSearch. Please check your .env file.")
        return

    # Check connection
    try:
        # Try basic info first (works for Provisioned)
        info = client.info()
        print(f"✅ Connected to OpenSearch! Version: {info['version']['number']}")
    except Exception as e:
        # Fallback for Serverless (AOSS) which returns 404 on root
        try:
            client.cat.indices(format="json")
            print("✅ Connected to OpenSearch Serverless (AOSS)!")
        except Exception as inner_e:
            print(f"❌ Connection failed: {e}")
            print(f"   (AOSS check also failed: {inner_e})")
            return

    index_name = 'inventory'

    # 2. Create Index (if it doesn't exist)
    index_body = {
        'settings': {
            'index': {
                'number_of_shards': 1,
                'number_of_replicas': 1
            }
        },
        'mappings': {
            'properties': {
                'name': {'type': 'text'},
                'category': {'type': 'keyword'},
                'price': {'type': 'float'},
                'in_stock': {'type': 'boolean'},
                'description': {'type': 'text'}
            }
        }
    }

    try:
        if not client.indices.exists(index=index_name):
            client.indices.create(index=index_name, body=index_body)
            print(f"✅ Created index: {index_name}")
        else:
            print(f"ℹ️ Index {index_name} already exists.")
    except Exception as e:
        print(f"❌ Error creating index: {e}")
        return

    # 3. Insert Data
    document = {
        'name': 'MacBook Pro 16',
        'category': 'Electronics',
        'price': 2499.99,
        'in_stock': True,
        'description': 'Powerful laptop for creative professionals.'
    }

    try:
        response = client.index(
            index=index_name,
            body=document
        )
        print(f"✅ Document inserted. Result: {response['result']}")
    except Exception as e:
        print(f"❌ Error inserting document: {e}")
        return

    # 4. Verify by Searching
    query = {
        'query': {
            'match': {
                'name': 'MacBook'
            }
        }
    }

    try:
        response = client.search(
            body=query,
            index=index_name
        )
        print(f"🔍 Search results (Total hits: {response['hits']['total']['value']}):")
        for hit in response['hits']['hits']:
            print(f"  - Found: {hit['_source']['name']} (${hit['_source']['price']})")
    except Exception as e:
        print(f"❌ Error during search: {e}")

if __name__ == "__main__":
    main()
