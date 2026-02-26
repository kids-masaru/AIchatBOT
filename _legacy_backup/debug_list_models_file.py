import google.generativeai as genai
import os
import sys
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get('GEMINI_API_KEY')
genai.configure(api_key=api_key)

with open('model_list.txt', 'w', encoding='utf-8') as f:
    f.write(f"Library Version: {genai.__version__}\n")
    f.write("--- Models ---\n")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                f.write(f"{m.name}\n")
    except Exception as e:
        f.write(f"Error: {e}\n")

print("Done writing to model_list.txt")
