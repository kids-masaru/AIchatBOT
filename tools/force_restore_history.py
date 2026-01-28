
import sys
import os
import json
from pathlib import Path

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.storage import _restore_from_drive, HISTORY_FILE, save_all_history, load_all_history

print("--- Force Restoring History from Drive ---")
restored_data = _restore_from_drive()

if restored_data:
    print(f"Time to overwrite local history.json with {len(restored_data)} users from Drive.")
    
    # Write directly to file to ensure overwrite
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(restored_data, f, ensure_ascii=False, indent=2)
        print("Success: history.json overwritten.")
    except Exception as e:
        print(f"Error writing file: {e}")
        
    # Verify
    print("Verifying content...")
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        for user, msgs in data.items():
            print(f"User: {user} | Messages: {len(msgs)}")
            if msgs:
                print(f"  Last: {msgs[-1].get('text')[:30]}...")
else:
    print("Failure: Could not restore from Drive (Found nothing or error).")
