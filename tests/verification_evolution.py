import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agent import load_skill
from utils.sheets_config import update_agent_instruction, load_config

def test_update_instruction():
    print("\n--- Testing update_agent_instruction ---")
    # Try updating Fumi (Maker)
    config_before = load_config()
    orig_instr = config_before.get("fumi_instruction", "")
    print(f"Original Fumi instruction length: {len(orig_instr)}")
    
    test_instr = orig_instr + "\n※語尾に「フミ！」とつけてください。"
    res = update_agent_instruction("fumi", test_instr)
    print(f"Update Result: {res}")
    
    if res.get("success"):
        config_after = load_config()
        new_instr = config_after.get("fumi_instruction", "")
        if "フミ！" in new_instr:
            print("✅ Update successful!")
        else:
            print("❌ Update failed (content mismatch).")
            
        # Restore original
        update_agent_instruction("fumi", orig_instr)
        print("Restored original instruction.")
    else:
        print("❌ Update failed.")

def test_load_skill():
    print("\n--- Testing load_skill ---")
    # This requires a 'KOTO_SKILLS' folder and a file in Drive
    # We can at least test the folder creation/retrieval part
    res = load_skill("non_existent_skill_test_12345")
    print(f"Load Skill Result (expected fail): {res}")
    
    if "見つかりませんでした" in str(res.get("error", "")):
        print("✅ Correct error for missing skill.")
    elif res.get("success"):
         print("⚠️ Unexpected success (did you have a file with that name?)")
    else:
        print(f"❌ Unexpected error type: {res.get('error')}")

if __name__ == "__main__":
    test_update_instruction()
    test_load_skill()
