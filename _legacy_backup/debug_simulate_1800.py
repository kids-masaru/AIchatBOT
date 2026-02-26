
import sys
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from utils.sheets_config import load_config

print("--- Simulation: Triggering Logic at 18:00 JST ---")

# Mock Time: 18:00:00 JST
jst = timezone(timedelta(hours=9))
# We can't easily mock datetime.now() inside the imported module without patching.
# Instead, let's copy the logic and run it 'as if' it were 18:00.

target_hour = 18
print(f"Simulating timestamp: [Any Date] {target_hour}:00:00 JST")

config = load_config()
reminders = config.get('reminders', [])

found_match = False
for r in reminders:
    if not r.get('enabled', True):
        print(f"Skipping disabled reminder: {r.get('time')}")
        continue

    r_time = r.get('time', '07:00')
    try:
        r_hour = int(r_time.split(':')[0])
    except:
        r_hour = 7
    
    print(f"Checking reminder {r_time} (Hour: {r_hour}) vs Target {target_hour}")
    
    if r_hour == target_hour:
        print(">>> MATCH FOUND! This reminder WOULD trigger.")
        print(f"    Message: {r.get('prompt')}")
        found_match = True
    else:
        print("    No match.")

if not found_match:
    print("FAILURE: No reminder matched 18:00.")
else:
    print("SUCCESS: Logic is correct. If Cron ran, this should have fired.")

print("\n--- Check: Timezone Logic ---")
now_utc = datetime.now(timezone.utc)
now_jst = now_utc.astimezone(jst)
print(f"Current System Time (UTC): {now_utc}")
print(f"Current System Time (JST): {now_jst}")
