
from google import genai
import os
from dotenv import load_dotenv
import sys

# Load environment variables
load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    print("Error: GEMINI_API_KEY not found.")
    sys.exit(1)

print("Attempting to connect with google-genai SDK...")

try:
    client = genai.Client(api_key=api_key)
    
    # Test Gemini 3 Flash Preview
    print("Testing gemini-3-flash-preview...")
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents="Hello, represent yourself."
    )
    print("Success!")
    print(f"Response: {response.text}")

except Exception as e:
    print(f"Error: {e}")
    # Fallback check list models if possible in this SDK
    try:
        print("Listing available models in new SDK (if supported)...")
        # Note: listing might be client.models.list() or similar, guessing API based on common patterns
        # or just fail.
    except:
        pass
