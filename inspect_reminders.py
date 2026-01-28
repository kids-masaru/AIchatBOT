
import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from utils.sheets_config import load_config

print("--- Checking Current Reminders Configuration ---")
try:
    config = load_config()
    reminders = config.get('reminders', [])
    
    if not reminders:
        print("No reminders found in config.")
    else:
        print(f"Found {len(reminders)} reminders:")
        for r in reminders:
            status = "ENABLED" if r.get('enabled') else "DISABLED"
            print(f"- Time: {r.get('time')} | Status: {status} | Message: {r.get('message')}")

except Exception as e:
    print(f"Error loading config: {e}")
