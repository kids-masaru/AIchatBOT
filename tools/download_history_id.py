
import sys
import os
import json

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.google_ops import read_drive_file
from utils.storage import HISTORY_FILE

FILE_ID = "1YRDgbxTMYcepu_q_KAbVcS0qZxpERHuZ"

print(f"Downloading history from ID: {FILE_ID}")
res = read_drive_file(FILE_ID)

if res.get("success"):
    content = res.get("content", "")
    if content:
        # Validate JSON
        try:
            data = json.loads(content)
            # Save
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print("Success: History restored.")
            
            # Print stats
            count = sum(len(msgs) for msgs in data.values())
            print(f"Restored {len(data)} users and {count} messages.")
        except Exception as e:
            print(f"Error parsing downloaded JSON: {e}")
    else:
        print("Error: Empty content from drive.")
else:
    print(f"Error reading drive file: {res.get('error')}")
