
import sys
import os

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from core.prompts import BASE_SYSTEM_PROMPT, TOOLS
    print("SUCCESS: core/prompts.py imported correctly.")
    print(f"System Prompt length: {len(BASE_SYSTEM_PROMPT)}")
    print(f"Tools count: {len(TOOLS)}")
    # Verify expert tools are gone
    expert_tools = [t['name'] for t in TOOLS if 'consult_' in t['name']]
    if expert_tools:
        print(f"WARNING: Expert tools still present: {expert_tools}")
    else:
        print("CONFIRMED: Expert tools removed.")
except Exception as e:
    print(f"FAILED: Import error in core/prompts.py: {e}")
    sys.exit(1)
