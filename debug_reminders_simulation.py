
import sys
import os
from datetime import datetime, timezone, timedelta

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.sheets_config import load_config

def test_reminders():
    print("--- Loading Configuration ---")
    config = load_config()
    reminders = config.get('reminders', [])
    
    print(f"Loaded {len(reminders)} reminders.")
    for i, r in enumerate(reminders):
        print(f"[{i}] Time: {r.get('time')} | Enabled: {r.get('enabled')} | Prompt: {r.get('prompt')[:20]}...")

    print("\n--- Simulating Check (JST) ---")
    # Simulate for 13:00
    test_hour = 13
    print(f"Testing for Hour: {test_hour}:00")
    
    triggered = []
    for r in reminders:
        if not r.get('enabled', True):
            continue
            
        r_time = r.get('time', '')
        try:
            # Simple check: "HH:MM"
            parts = r_time.split(':')
            r_hour = int(parts[0])
            
            if r_hour == test_hour:
                triggered.append(r)
        except Exception as e:
            print(f"Error parsing time '{r_time}': {e}")
            
    if triggered:
        print(f"SUCCESS: Would trigger {len(triggered)} reminder(s).")
    else:
        print("FAILURE: No reminders matched 13:00.")

if __name__ == "__main__":
    test_reminders()
