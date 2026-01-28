
import sys
import os
import json
from dotenv import load_dotenv

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load env locally
load_dotenv()

from utils.vector_store import get_user_profile
from utils.user_db import get_active_users

print("--- System Audit: Pinecone Profile Data ---")

# 1. Identify Target User
users = get_active_users()
if not users:
    print("Error: No active users found in Sheet DB.")
    sys.exit(1)

target_user_id = users[0]['user_id']
print(f"Target User ID: {target_user_id}")

# 2. Fetch from Pinecone
print("Fetching profile from Pinecone...")
try:
    profile = get_user_profile(target_user_id)
    print("--- Raw Data from Pinecone ---")
    print(json.dumps(profile, ensure_ascii=False, indent=2))
    print("------------------------------")
    
    if not profile:
        print("RESULT: Profile is EMPTY/NULL in Pinecone.")
    elif not profile.get('name'):
         print("RESULT: Profile exists but seems empty (no name/traits).")
    else:
        print("RESULT: Profile exists and looks populated.")
        
except Exception as e:
    print(f"Error fetching from Pinecone: {e}")

print("\n--- End Audit ---")
