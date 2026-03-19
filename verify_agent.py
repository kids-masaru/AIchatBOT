
import sys
import os

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from core.agent import get_gemini_response
    print("SUCCESS: core/agent.py imported correctly.")
    
    # Mock call (dry run)
    response = get_gemini_response("test_user_id", "こんにちは", client_config={"spreadsheet_id": "none"})
    print(f"Agent response preview: {response[:50]}...")
    
except Exception as e:
    print(f"FAILED: Import/Runtime error in core/agent.py: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
