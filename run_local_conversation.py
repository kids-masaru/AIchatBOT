import os
import sys
import time
from dotenv import load_dotenv

# Load env
load_dotenv()

from core.agent import get_gemini_response

def main():
    print("=== Koto Local Debug Client ===")
    print("Type 'exit' to quit.")

    # Initialize user_id
    user_id = "local_debug_user"

    while True:
        try:
            user_input = input("\nYou: ")
            if user_input.lower() in ['exit', 'quit']:
                break
                
            print("Koto thinking...", end="", flush=True)
            
            # get_gemini_response is synchronous
            response = get_gemini_response(user_id, user_input)
            
            print(f"\rKoto: {response}")
            
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
