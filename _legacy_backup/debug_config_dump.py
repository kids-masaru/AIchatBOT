from utils.sheets_config import load_config
import json
import sys

print("Fetching Live Configuration...")
try:
    config = load_config()
    
    # Extract Agent Settings
    agents = config.get("agents", {})
    
    print("\n--- KOTO (Main Agent) ---")
    print(f"System Prompt: {config.get('system_prompt', 'N/A')[:100]}...")
    
    print("\n--- SHIORI (Biographer) ---")
    shiori = agents.get("profiler", {}) # Check key name in sheets_config
    if not shiori: shiori = agents.get("biographer", {})
    print(f"Enabled: {shiori.get('enabled')}")
    print(f"Prompt: {shiori.get('prompt', 'N/A')}")
    
    print("\n--- FUMI (Maker) ---")
    fumi = agents.get("maker", {})
    print(f"Enabled: {fumi.get('enabled')}")
    print(f"Prompt: {fumi.get('prompt', 'N/A')}")
    
    # Check if these are actually used in core/prompts or agent?
    # Verification will continue in next steps.

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Config load error: {e}")
