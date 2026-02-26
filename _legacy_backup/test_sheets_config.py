from dotenv import load_dotenv
import os
import sys

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.sheets_config import load_config, save_config

print("Testing Sheets Config...")

# 1. Load config
print("\n[1] Loading config...")
config = load_config()
print(f"Loaded: {config}")

# 2. Modify and save
print("\n[2] Saving modified config...")
config['user_name'] = 'テストユーザー'
result = save_config(config)
print(f"Save result: {result}")

# 3. Reload to verify
print("\n[3] Reloading to verify...")
config2 = load_config()
print(f"Reloaded: {config2}")

if config2.get('user_name') == 'テストユーザー':
    print("\n✅ SUCCESS! Sheets config is working!")
else:
    print("\n❌ FAILED - Config not saved correctly")
