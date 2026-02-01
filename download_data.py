import json
import os
from utils import get_opensearch_client

def download_index_data(index_name, output_file=None):
    """
    Downloads ALL documents from an OpenSearch index using 'search_after' for deep pagination.
    Saves in NDJSON format (one JSON object per line) which is efficient for large datasets (1GB+).
    """
    print(f"🔄 Connecting to OpenSearch to download '{index_name}'...")
    client = get_opensearch_client()
    
    if not client:
        print("❌ Could not connect to OpenSearch.")
        return

    try:
        if not client.indices.exists(index=index_name):
            print(f"❌ Index '{index_name}' does not exist.")
            return

        # 1. Get total count
        count_resp = client.count(index=index_name)
        total_docs = count_resp['count']
        print(f"ℹ️ Found {total_docs} documents in '{index_name}'. Starting download...")

        if not output_file:
            output_file = f"{index_name}_data.jsonl" # .jsonl for Newline Delimited JSON

        # 2. Setup Search with 'search_after'
        # We need a consistent sort order. Using _id is good for unique tie-breaking.
        # Note: AOSS may not support _seq_no/_primary_term for sorting. Using _id is safer.
        sort_query = [{"_id": "asc"}] 
        
        # Batch size (1000 is a reasonable balance)
        batch_size = 1000
        
        with open(output_file, 'w', encoding='utf-8') as f:
            # Initial search
            response = client.search(
                index=index_name,
                body={
                    "query": {"match_all": {}},
                    "sort": sort_query
                },
                size=batch_size
            )
            
            hits = response['hits']['hits']
            downloaded = 0
            
            while hits:
                # Write batch to file
                for hit in hits:
                    json.dump(hit['_source'], f)
                    f.write('\n')
                
                downloaded += len(hits)
                print(f"   Downloaded {downloaded}/{total_docs}...", end='\r')
                
                # Setup next request
                last_hit = hits[-1]
                sort_values = last_hit['sort']
                
                response = client.search(
                    index=index_name,
                    body={
                        "query": {"match_all": {}},
                        "sort": sort_query,
                        "search_after": sort_values
                    },
                    size=batch_size
                )
                hits = response['hits']['hits']

        print(f"\n✅ Successfully saved {downloaded} documents to '{output_file}'")
        print(f"ℹ️ Format is NDJSON (newline delimited). Each line is a valid JSON object.")

    except Exception as e:
        print(f"\n❌ Error downloading data: {e}")
        # Fallback suggestion if _seq_no fails (some very old ES versions or specific AOSS configs)
        print("Tip: If sorting fails, try sorting by a specific field like 'created_at' or '_id'.")

if __name__ == "__main__":
    import sys
    idx = sys.argv[1] if len(sys.argv) > 1 else 'inventory'
    download_index_data(idx)
