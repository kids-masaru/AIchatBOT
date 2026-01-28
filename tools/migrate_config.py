
import sys
import os
import json
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from utils.sheets_config import load_config, save_config, DEFAULT_CONFIG

print("--- Migrating Config to Multi-Agent Schema ---")

# 1. Load current (old) config
old_config = load_config()
print(f"Loaded old config keys: {list(old_config.keys())}")

# 2. Create new config based on DEFAULT (full schema)
new_config = DEFAULT_CONFIG.copy()

# 3. Map old values to new keys to preserve user settings
# Global
if 'user_name' in old_config:
    new_config['user_name'] = old_config['user_name']

# Koto
if 'personality' in old_config:
    new_config['koto_personality'] = old_config['personality']
    print(f"Migrated personality -> koto_personality")

if 'master_prompt' in old_config:
    new_config['koto_master_prompt'] = old_config['master_prompt']
    print(f"Migrated master_prompt -> koto_master_prompt")

# Reminders (Keep existing list)
if 'reminders' in old_config and old_config['reminders']:
    new_config['reminders'] = old_config['reminders']
    print(f"Preserved {len(new_config['reminders'])} reminders")

# Knowledge Sources
if 'knowledge_sources' in old_config:
    new_config['knowledge_sources'] = old_config['knowledge_sources']

# Notion
if 'notion_databases' in old_config:
    new_config['notion_databases'] = old_config['notion_databases']

# Experts (Rename if exists)
if 'expert_history_instruction' in old_config:
    new_config['toki_instruction'] = old_config['expert_history_instruction']
if 'expert_comms_instruction' in old_config:
    new_config['ren_instruction'] = old_config['expert_comms_instruction']

# 4. Save new config
print("Saving new expanded configuration...")
success = save_config(new_config)

if success:
    print("SUCCESS: Config migration complete.")
    print("New keys available in sheet:")
    for key in new_config.keys():
        print(f" - {key}")
else:
    print("FAILURE: Could not save new config.")
