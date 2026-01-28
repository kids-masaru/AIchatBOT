
import sys
import os
from dotenv import load_dotenv

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load env locally
load_dotenv()

from utils.vector_store import _get_index

print("--- Debug: Listing Pinecone Content ---")
try:
    index = _get_index()
    if not index:
        print("Error: Could not connect to Index.")
        sys.exit(1)

    print(f"Connected to Index.")
    
    # Check stats
    stats = index.describe_index_stats()
    print(f"Stats: {stats}")
    
    # List IDs in Default Namespace
    print("\n--- IDs in Default Namespace ---")
    try:
        # iterate via list (if available in client version) or query dummy
        # Pinecone client 3.0+ has .list() (Serverless/Pod)
        for ids in index.list(prefix='profile:'):
            print(f"Found IDs (profile:): {ids}")
            
        print("Listing first 10 generic IDs...")
        for ids in index.list(limit=10):
            print(ids)
            
    except Exception as e:
        print(f"List error: {e}")
        # Fallback: Query for everything
        
except Exception as e:
    print(f"General Error: {e}")
