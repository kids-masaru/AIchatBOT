import sys
import os
from core.agent import get_gemini_response

print("Testing get_gemini_response...")
try:
    response = get_gemini_response("test_user_id", "1+1は？")
    print("SUCCESS! Response:")
    print(response)
except Exception as e:
    print("FAILED!")
    import traceback
    traceback.print_exc()
