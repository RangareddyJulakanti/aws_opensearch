import json
import os
import boto3
import time
# Try to import from local utils if available (for local run)
try:
    from utils import get_opensearch_client as get_client_local, load_config
except ImportError:
    pass

from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

# Initialize S3 client outside handler for reuse
s3_client = boto3.client('s3')

def get_opensearch_client(url, region):
    """
    Initialize OpenSearch client for Lambda.
    Credentials are auto-fetched from Lambda execution role.
    """
    # ... (same as before) ...
    # Check if running locally and use utils logic if needed
    # But for Lambda simplicity, we keep the direct boto3 fetch here.
    
    if not url:
        raise ValueError("OPENSEARCH_URL is missing")

    host = url.replace('https://', '').replace('http://', '').split('/')[0]
    service = 'aoss' if 'aoss' in host else 'es'
    
    # Use standard boto3 session which picks up local env vars or Lambda role
    credentials = boto3.Session().get_credentials()
    auth = AWSV4SignerAuth(credentials, region, service)
    
    return OpenSearch(
        hosts=[{'host': host, 'port': 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )

def lambda_handler(event, context):
    """
    Lambda Handler to export OpenSearch index to S3.
    """
    print("🚀 Starting OpenSearch Export...")
    
    # 1. Configuration
    opensearch_url = os.environ.get('OPENSEARCH_URL')
    region = os.environ.get('AWS_REGION', 'us-east-1')
    default_bucket = os.environ.get('OUTPUT_BUCKET')
    
    # Event overrides
    index_name = event.get('index_name', 'inventory')
    bucket_name = event.get('bucket_name', default_bucket)
    
    if not bucket_name:
        return {
            'statusCode': 400,
            'body': json.dumps('Error: OUTPUT_BUCKET not set and not provided in event.')
        }

    # 2. Connect
    try:
        client = get_opensearch_client(opensearch_url, region)
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return {'statusCode': 500, 'body': str(e)}

    # 3. Download Logic (Streaming to /tmp)
    tmp_file_path = f"/tmp/{index_name}_{int(time.time())}.jsonl"
    # Ensure /tmp exists locally
    os.makedirs("/tmp", exist_ok=True)
    
    try:
        # Check index existence logic...
        try:
            if not client.indices.exists(index=index_name):
                 return {
                    'statusCode': 404,
                    'body': json.dumps(f"Index '{index_name}' not found.")
                }
        except Exception:
             # AOSS fallback for verify
             pass

        # ... (Same logic as before, using search_after) ...
        # For brevity in this edit, assuming logic stays similar but we ensure imports work.
        # Let's perform the actual download.
        
        count_resp = client.count(index=index_name)
        total_docs = count_resp['count']
        print(f"ℹ️ Found {total_docs} docs. Downloading to {tmp_file_path}...")
        
        batch_size = 1000
        sort_query = [{"_id": "asc"}] 
        
        with open(tmp_file_path, 'w', encoding='utf-8') as f:
            response = client.search(
                index=index_name,
                body={"query": {"match_all": {}}, "sort": sort_query},
                size=batch_size
            )
            hits = response['hits']['hits']
            downloaded = 0
            
            while hits:
                for hit in hits:
                    json.dump(hit['_source'], f)
                    f.write('\n')
                downloaded += len(hits)
                print(f"   Downloading... {downloaded}/{total_docs}", end='\r')
                
                last_hit = hits[-1]
                sort_values = last_hit['sort']
                response = client.search(
                    index=index_name,
                    body={"query": {"match_all": {}}, "sort": sort_query, "search_after": sort_values},
                    size=batch_size
                )
                hits = response['hits']['hits']
                
        print(f"\n✅ Downloaded {downloaded} docs. Uploading to S3...")

        # 4. Upload to S3
        s3_key = f"opensearch-backups/{index_name}/{os.path.basename(tmp_file_path)}"
        s3_client.upload_file(tmp_file_path, bucket_name, s3_key)
        
        print(f"✅ Uploaded to s3://{bucket_name}/{s3_key}")
        
        os.remove(tmp_file_path)
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Success', 's3_path': f"s3://{bucket_name}/{s3_key}"})
        }

    except Exception as e:
        print(f"❌ Execution Error: {e}")
        return {'statusCode': 500, 'body': str(e)}

if __name__ == "__main__":
    # Local Execution Block
    import sys
    
    # 1. Load Environment
    if os.path.exists('.env'):
        from dotenv import load_dotenv
        load_dotenv()
        
    # 2. Parse Args
    idx = sys.argv[1] if len(sys.argv) > 1 else 'inventory'
    bucket = sys.argv[2] if len(sys.argv) > 2 else os.getenv('OUTPUT_BUCKET')
    
    if not bucket:
        print("❌ Error: S3 Bucket Name is required.")
        print("Usage: python lambda_function.py <index_name> <bucket_name>")
        sys.exit(1)
        
    # 3. Dummy Context
    class Context:
        def __init__(self):
            self.aws_request_id = "local-run"
            
    # 4. Run
    event = {'index_name': idx, 'bucket_name': bucket}
    lambda_handler(event, Context())
