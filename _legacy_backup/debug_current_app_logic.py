import sys
import os
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.sheets_config import load_config

def test_current_logic():
    print("--- Testing Current Application Logic ---")
    try:
        config = load_config()
        print("\n[Result Loaded by App Logic]")
        
        # Check specific key fields
        reminders = config.get('reminders', [])
        print(f"Reminders Count: {len(reminders)}")
        for r in reminders:
            print(f" - {r.get('time')} ({r.get('name')}) Enabled:{r.get('enabled')}")
            
        # Check to distinguish from default
        if len(reminders) == 2 and reminders[0]['time'] == '07:00' and reminders[0]['name'] == 'Morning Briefing':
            print("\n[CONCLUSION] This matches the DEFAULT CONFIG (Fallback).")
            print("The app failed to read the Sheet values.")
        else:
            print("\n[CONCLUSION] This matches the SHEET CONFIG.")
            print("The app successfully read the Sheet values.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_current_logic()
