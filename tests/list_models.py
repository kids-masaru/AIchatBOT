"""
List available Gemini models
"""
import os
from dotenv import load_dotenv
load_dotenv()

import google.generativeai as genai

api_key = os.environ.get("GEMINI_API_KEY")
print(f"API Key present: {bool(api_key)}")

genai.configure(api_key=api_key)

print("\n--- Available Generate Models ---")
for m in genai.list_models():
    if "generateContent" in m.supported_generation_methods:
        print(f"  {m.name}")
        
print("\n--- Testing gemini-2.0-flash ---")
try:
    m = genai.GenerativeModel("gemini-2.0-flash")
    r = m.generate_content("Say hi")
    print(f"SUCCESS: {r.text[:50]}")
except Exception as e:
    print(f"FAIL: {e}")
    
print("\n--- Testing gemini-1.5-flash ---")
try:
    m = genai.GenerativeModel("gemini-1.5-flash")
    r = m.generate_content("Say hi")
    print(f"SUCCESS: {r.text[:50]}")
except Exception as e:
    print(f"FAIL: {e}")
