import google.generativeai as genai
import os
import sys
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get('GEMINI_API_KEY')
genai.configure(api_key=api_key)

print("Testing generation with gemini-3-flash-preview...")
try:
    model = genai.GenerativeModel("gemini-3-flash-preview")
    response = model.generate_content("Hello, are you Gemini 3?")
    print(f"Success! Response: {response.text}")
except Exception as e:
    print(f"Failed: {e}")

print("\nTesting generation with gemini-2.5-flash...")
try:
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content("Hello, are you Gemini 2.5?")
    print(f"Success! Response: {response.text}")
except Exception as e:
    print(f"Failed: {e}")
