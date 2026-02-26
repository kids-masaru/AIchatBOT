import os
from dotenv import load_dotenv
load_dotenv()

from google import genai
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

print("--- Embedding Models ---")
try:
    for m in client.models.list():
        methods = str(getattr(m, 'supported_generation_methods', getattr(m, 'supported_actions', [])))
        if "embedContent" in methods:
            print(f"- {m.name}")
except Exception as e:
    print(e)

print("\n--- Generation Models (flash) ---")
try:
    for m in client.models.list():
        methods = str(getattr(m, 'supported_generation_methods', getattr(m, 'supported_actions', [])))
        if "generateContent" in methods and "flash" in m.name.lower():
            print(f"- {m.name}")
except Exception as e:
    print(e)
