import inspect
from typing import List, Dict, Any, Callable

def function_to_schema(func: Callable) -> Dict[str, Any]:
    """
    Convert a Python function to OpenAI function schema.
    Extracts name, description, and parameters from docstring and type hints.
    """
    name = func.__name__
    doc = func.__doc__ or ""
    desc = doc.split("\n")[0].strip()
    
    sig = inspect.signature(func)
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue
            
        param_type = "string" # Default
        if param.annotation == int:
            param_type = "integer"
        elif param.annotation == bool:
            param_type = "boolean"
        elif param.annotation == float:
            param_type = "number"
        elif param.annotation == dict:
            param_type = "object"
        elif param.annotation == list:
            param_type = "array"
            
        # Extract description from docstring if possible (simple heuristic)
        # Assuming Google style docstring for now based on checked files
        param_desc = ""
        if "Args:" in doc:
            args_section = doc.split("Args:")[1]
            for line in args_section.split("\n"):
                if param_name in line:
                    param_desc = line.split(":", 1)[1].strip() if ":" in line else ""
                    break
        
        parameters["properties"][param_name] = {
            "type": param_type,
            "description": param_desc
        }
        
        if param.default == inspect.Parameter.empty:
            parameters["required"].append(param_name)
            
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": parameters
        }
    }

def get_tool_schemas(tools: List[Callable]) -> List[Dict[str, Any]]:
    """Convert a list of functions to OpenAI tool schemas"""
    return [function_to_schema(func) for func in tools]
