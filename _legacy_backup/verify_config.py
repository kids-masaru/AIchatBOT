import sys
import os
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.sheets_config import load_config

def verify_config_update():
    """
    Verify that the 'shiori_instruction' in the Google Sheet 
    contains the expected Japanese translation directive.
    """
    print("Verifying config from Sheets...")
    config = load_config()
    instruction = config.get('shiori_instruction', '')
    
    # Key phrases to check
    checks = [
        "言語制約",
        "完全に日本語",
        "日本語に翻訳"
    ]
    
    all_passed = True
    for check in checks:
        if check in instruction:
            print(f"PASS: Found '{check}' in instruction.")
        else:
            print(f"FAIL: '{check}' not found in instruction.")
            all_passed = False
            
    if all_passed:
        print("\nSUCCESS: Verification passed! The live configuration is updated.")
        # Print a snippet
        print("\nSnippet:")
        print(instruction[:200] + "...")
    else:
        print("\nFAILURE: Configuration does not match likely target.")

if __name__ == "__main__":
    verify_config_update()
