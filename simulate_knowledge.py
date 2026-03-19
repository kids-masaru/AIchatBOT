
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.agent import get_gemini_response

def simulate_with_config(text):
    print(f"--- Simulating: {text} ---")
    # Mock client config
    client_config = {
        "spreadsheet_id": "none", # Will trigger search or error, but we want to check logic
        "bot_name": "TestBot"
    }
    try:
        # In a real run, this would trigger tool call. 
        # Here we just check if the agent logic starts without import errors.
        response = get_gemini_response("user_123", text, client_config=client_config)
        print(f"Response: {response[:100]}...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    simulate_with_config("今日決まったことを共通知識に保存して：来週の月曜日は定休日です。")
