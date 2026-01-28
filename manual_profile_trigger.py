import sys
import os

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, run_profiler
from utils.storage import add_message
from utils.user_db import get_active_users

print("Triggering Manual Profiler Run...", file=sys.stderr)

# 1. Ensure target user has history (Kickstart)
users = get_active_users()
if users:
    target_user = users[0]['user_id']
    print(f"Target User: {target_user}", file=sys.stderr)
    
# 1. Ensure target user has history (Kickstart)
users = get_active_users()
if users:
    target_user = users[0]['user_id']
    print(f"Target User: {target_user}", file=sys.stderr)
    
    # Load Real History
    from utils.storage import get_user_history
    hist = get_user_history(target_user)
    
    # DEBUG: Filter only user messages and print count
    user_msgs = [m['text'] for m in hist if m['role'] == 'user']
    print(f"Found {len(user_msgs)} user messages in history.", file=sys.stderr)
    
    if not user_msgs:
         print("Warning: History is empty. Profiler will have nothing to analyze.", file=sys.stderr)
    
    # We don't need to inject dummy data if real data exists. 
    # If real data is empty, injecting dummy data is confusing.
    # But user specifically asked "Use my past signals".
    # So if zero, we warn.
    
run_profiler()
print("Profiler Run Initiated.", file=sys.stderr)
