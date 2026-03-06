import os
import sys
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

def get_weather(location: str):
    """Get the current weather for a location."""
    return f"The weather in {location} is sunny."

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

system_text = "You are a helpful assistant."
gemini_tools = [get_weather]

contents = [types.Content(role="user", parts=[types.Part.from_text(text="What is the weather in Tokyo?")])]

response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents=contents,
    config=types.GenerateContentConfig(
        system_instruction=system_text,
        tools=gemini_tools, 
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
    )
)

print("First Response:", response.text)
parts = response.candidates[0].content.parts
function_calls = [p.function_call for p in parts if p.function_call]

for fc in function_calls:
    print(f"Calling: {fc.name} with {fc.args}")
    
    # Try the manual response appending
    tool_responses = [types.Part.from_function_response(
        name=fc.name,
        response={'result': get_weather(**fc.args)}
    )]
    
    # Add model's call
    contents.append(response.candidates[0].content)
    # Add function response back
    contents.append(types.Content(role="user", parts=tool_responses))
    
    try:
        response2 = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_text,
                tools=gemini_tools, 
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
            )
        )
        print("Second Response (user role):", response2.text)
    except Exception as e:
        print("Error with role=user:", e)

    # Try with role="function" or "tool"
    contents.pop()
    contents.append(types.Content(role="function", parts=tool_responses))
    try:
        response3 = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_text,
                tools=gemini_tools, 
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
            )
        )
        print("Second Response (function role):", response3.text)
    except Exception as e:
        print("Error with role=function:", e)

