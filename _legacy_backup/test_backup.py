import sys
import os
from utils.storage import add_message, save_all_history, load_all_history

print("Testing backup logic...")
try:
    # 1. Add a dummy message to trigger save/backup
    # But wait, save_all_history runs in a thread. We might exit before it finishes.
    # We should run the backup logic synchronously for testing.
    
    # Let's extract the backup logic or just invoke save_all_history and wait.
    print("Adding test message...")
    add_message("test_user_123", "user", "Test backup message")
    
    # Wait a bit for thread
    import time
    print("Waiting for background thread (5s)...")
    time.sleep(5)
    
    # Check if file exists
    from tools.google_ops import search_drive
    res = search_drive("koto_history_backup.json")
    if res.get("files"):
        print(f"SUCCESS: Found backup file: {res['files'][0]['name']}")
    else:
        print("FAILURE: Backup file NOT found after test.")

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Test failed with error: {e}")
