import sys
from google import genai
from google.genai import types

TOOLS = [
    {
        "name": "calculate",
        "description": "Test tool",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {"type": "string"}
            },
            "required": ["expression"]
        }
    }
]

try:
    config = types.GenerateContentConfig(
        tools=[types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name=t["name"],
                    description=t["description"],
                    parameters=t["parameters"]
                ) for t in TOOLS
            ]
        )]
    )
    print("SUCCESS")
except Exception as e:
    print(f"ERROR: {e}")
