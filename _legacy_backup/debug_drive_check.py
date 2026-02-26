from tools.google_ops import search_drive
import sys

# Check for backup file
print("Searching for backup file...")
res = search_drive("koto_history_backup.json")
if res.get("files"):
    print(f"Found backup file: {res['files'][0]['name']} (ID: {res['files'][0]['id']})")
else:
    print("Backup file NOT found.")
