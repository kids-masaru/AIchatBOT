"""
Test Gemini API with different configurations
"""
import os
from dotenv import load_dotenv
load_dotenv()

import google.generativeai as genai

api_key = os.environ.get("GEMINI_API_KEY")
print(f"API Key: {api_key[:10]}... ({len(api_key)} chars)")

genai.configure(api_key=api_key)

# List all available models correctly
print("\n=== Available Models for generateContent ===")
for m in genai.list_models():
    if "generateContent" in m.supported_generation_methods:
        print(f"  {m.name}")

# Test 1: Simple call WITHOUT tools
print("\n=== Test 1: No-Tools Call (gemini-1.5-flash) ===")
try:
    m = genai.GenerativeModel("gemini-1.5-flash")
    r = m.generate_content("Say 'test OK' in Japanese")
    print(f"SUCCESS: {r.text}")
except Exception as e:
    print(f"FAIL: {e}")

# Test 2: Call WITH simple tools
print("\n=== Test 2: With-Tools Call (gemini-1.5-flash) ===")
try:
    tools = [genai.protos.Tool(function_declarations=[
        genai.protos.FunctionDeclaration(
            name="test_func",
            description="A test function",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={"arg1": genai.protos.Schema(type=genai.protos.Type.STRING, description="Test arg")},
                required=["arg1"]
            )
        )
    ])]
    m = genai.GenerativeModel("gemini-1.5-flash", tools=tools)
    r = m.generate_content("Say 'test OK' in Japanese")
    print(f"SUCCESS: {r.text}")
except Exception as e:
    print(f"FAIL: {e}")

# Test 3: Try gemini-pro instead
print("\n=== Test 3: gemini-pro (No Tools) ===")
try:
    m = genai.GenerativeModel("gemini-pro")
    r = m.generate_content("Say 'test OK' in Japanese")
    print(f"SUCCESS: {r.text}")
except Exception as e:
    print(f"FAIL: {e}")
    
print("\n=== DONE ===")
