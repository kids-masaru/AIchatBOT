"""
Minimal Gemini API Test
"""
import os
from dotenv import load_dotenv
load_dotenv()

import google.generativeai as genai

api_key = os.environ.get("GEMINI_API_KEY")
print(f"API Key: {api_key[:10]}... (length: {len(api_key) if api_key else 0})")

if not api_key:
    print("ERROR: GEMINI_API_KEY not found!")
else:
    genai.configure(api_key=api_key)
    
    # List available models
    print("\n--- Available Models ---")
    for m in genai.list_models():
        if "generateContent" in m.supported_generation_methods:
            print(f"  {m.name}")
    
    # Try a simple call
    print("\n--- Test Call ---")
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content("Say 'Hello World' in Japanese")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"ERROR: {e}")
