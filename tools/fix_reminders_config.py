
import sys
import os
import json
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from utils.sheets_config import load_config, save_config

print("--- Fixing Reminders Configuration ---")

# 1. Load current config (to preserve other settings like prompts/personality)
current_config = load_config()

# 2. Define the correct multi-reminder structure
# Restoring 7:00 and keeping 18:00
new_reminders = [
    {
        "name": "Morning Briefing",
        "time": "07:00",
        "prompt": "今日の天気、今日・明日・今週の予定とタスクを確認して、まとめて教えて！最後に今日も頑張ろうという気持ちになる一言をお願い！",
        "enabled": True
    },
    {
        "name": "Evening Check-in",
        "time": "18:00",
        "prompt": "今日の業務の振り返りをして。まだ残っているタスクがないか確認して。明日の予定も軽く教えて。",
        "enabled": True
    }
]

current_config['reminders'] = new_reminders

print("Saving updated configuration...")
print(json.dumps(new_reminders, indent=2, ensure_ascii=False))

success = save_config(current_config)

if success:
    print("SUCCESS: Config updated with 2 reminders.")
else:
    print("FAILURE: Could not save config.")
