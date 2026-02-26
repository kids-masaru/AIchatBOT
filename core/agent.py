"""
Koto Agent - AI Logic (Gemini API Version)
Handles conversation with Google Gemini API and tool execution.
"""
import os
import sys
import json
import datetime
from google import genai
from google.genai import types

from core.prompts import BASE_SYSTEM_PROMPT, TOOLS
from utils.storage import get_user_history, add_message

# Config
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Tools Import
from tools.basic_ops import calculate, calculate_date, search_and_read_pdf
from tools.web_ops import google_web_search, fetch_url
from tools.weather import get_current_weather
from tools.google_ops import (
    create_google_doc, create_google_sheet, create_google_slide,
    create_drive_folder, move_drive_file, rename_file, search_drive,
    list_gmail, get_gmail_body, create_gmail_draft, get_latest_uploads,
    list_calendar_events, create_calendar_event, find_free_slots,
    list_tasks, add_task
)
from tools.notion_ops import list_notion_tasks, create_notion_task, update_notion_task
from tools.template_ops import (
    list_templates, check_unregistered_templates, find_template_by_type,
    copy_template, register_template, replace_placeholders
)

# --- Tool Wrapper Functions (Clean names for Gemini) ---
# ... (Wrappers are same as before, simplified for brevity in this restoration if possible, 
# or just mapped directly. Gemini SDK handles functions well. 
# We need to map the 'name' in TOOLS list to actual functions.)

def consult_fumi(request: str) -> dict:
    from core.maker import maker
    return {"expert": "Fumi", "response": maker.run(request)}

def consult_aki(request: str) -> dict:
    from core.librarian import librarian
    return {"expert": "Aki", "response": librarian.run(request)}

def consult_toki(request: str) -> dict:
    from core.historian import historian
    return {"expert": "Toki", "response": historian.run(request)}

def consult_ren(request: str) -> dict:
    from core.communicator import communicator
    return {"expert": "Ren", "response": communicator.run(request)}

def consult_rina(request: str) -> dict:
    from core.scheduler import scheduler
    return {"expert": "Rina", "response": scheduler.run(request)}

_current_user_id = None
def set_reminder(location: str) -> dict:
    if not _current_user_id: return {"error": "User ID missing"}
    from utils.user_db import register_user
    return register_user(_current_user_id, location)

def use_template(template_type: str, new_document_name: str) -> dict:
    result = find_template_by_type(template_type)
    if result.get("error"): return result
    if not result.get("found"):
        return {"error": f"Template '{template_type}' not found."}
    
    template = result["template"]
    copy_result = copy_template(template["file_id"], new_document_name)
    if copy_result.get("error"): return copy_result
    
    return {
        "success": True,
        "message": f"Created '{new_document_name}' from template '{template['name']}'.",
        "url": copy_result.get("url"),
        "template_fields": template.get("fields", [])
    }

def register_new_template(file_id: str, name: str, template_type: str, description: str, fields: str, usage_hint: str) -> dict:
    fields_list = [f.strip() for f in fields.split(',')] if fields else []
    return register_template(file_id, name, template_type, description, fields_list, usage_hint)


# Map tool names to functions
KOTO_TOOLS = {
    'calculate': calculate,
    'calculate_date': calculate_date,
    'search_and_read_pdf': search_and_read_pdf,
    'google_web_search': google_web_search,
    'get_current_weather': get_current_weather,
    'fetch_url': fetch_url,
    'create_google_doc': create_google_doc,
    'create_google_sheet': create_google_sheet,
    'create_google_slide': create_google_slide,
    'create_drive_folder': create_drive_folder,
    'move_drive_file': move_drive_file,
    'rename_file': rename_file,
    'search_drive': search_drive,
    'list_gmail': list_gmail,
    'get_gmail_body': get_gmail_body,
    'create_draft': create_gmail_draft,
    'get_recent_uploads': get_latest_uploads,
    'list_calendar_events': list_calendar_events,
    'create_calendar_event': create_calendar_event,
    'find_free_slots': find_free_slots,
    'list_tasks': list_tasks,
    'add_task': add_task,
    'get_notion_tasks': lambda filter_today_only=False: list_notion_tasks(
        (lambda: (lambda c: c.get("notion_databases", [])[0].get("id", "") if c.get("notion_databases") else "")(__import__("utils.sheets_config", fromlist=["load_config"]).load_config()))(), 
        filter_today_only
    ), # Inline lambda to get config dynamically as in wrapper
    'add_notion_task': lambda title, due_date=None: create_notion_task(
        (lambda: (lambda c: c.get("notion_databases", [])[0].get("id", "") if c.get("notion_databases") else "")(__import__("utils.sheets_config", fromlist=["load_config"]).load_config()))(),
        title, due_date, None
    ),
    'complete_notion_task': lambda page_id, new_status: update_notion_task(page_id, new_status, None),
    'set_reminder': set_reminder,
    'consult_fumi': consult_fumi,
    'consult_aki': consult_aki,
    'consult_toki': consult_toki,
    'consult_ren': consult_ren,
    'consult_rina': consult_rina,
    'list_available_templates': list_templates,
    'check_new_templates': check_unregistered_templates,
    'find_template': find_template_by_type,
    'use_template': use_template,
    'register_new_template': register_new_template,
    'doc_replace_text': replace_placeholders
}

def analyze_document_layout(image_data: bytes, mime_type: str) -> dict:
    """Analyze document layout using Gemini Vision"""
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        prompt = """この画像を詳細に分析し、ドキュメントの構造、タイトル、セクション、重要な値を教えてください。
特に、これが領収書や請求書であれば、金額や日付、発行元を特定してください。
JSONでの出力は必須ではありませんが、構造がわかるように記述してください。"""

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=prompt),
                        types.Part.from_bytes(data=image_data, mime_type=mime_type)
                    ]
                )
            ]
        )
        return {"success": True, "structure": None, "raw": response.text}

    except Exception as e:
        print(f"Vision analysis error: {e}", file=sys.stderr)
        return {"error": str(e)}


def get_gemini_response(user_id, user_message, image_data=None, mime_type=None):
    """
    Main Agent Logic using Google Gemini API directly.
    """
    global _current_user_id
    _current_user_id = user_id
    
    if not GEMINI_API_KEY:
        return "エラー: GEMINI_API_KEYが設定されていません。"

    from utils.vector_store import save_conversation, get_user_profile, get_context_summary
    
    # Save input to memory
    save_conversation(user_id, "user", user_message)

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # 1. Build System Prompt & History
        add_message(user_id, "user", user_message)
        history_data = get_user_history(user_id)
        
        from utils.sheets_config import load_config
        config = load_config()
        
        personality = config.get("koto_personality", "明るくて元気なAI秘書")
        master_prompt = config.get("koto_master_prompt", "")
        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S (%A)')
        
        user_data = get_user_profile(user_id)
        profile_text = user_data.get('profile', '')
        memory_text = get_context_summary(user_id, user_message)
        user_name = config.get('user_name', 'ユーザー')
        knowledge_sources = config.get('knowledge_sources', [])
        
        system_text = f"{BASE_SYSTEM_PROMPT}\n現在の時間は {now_str} です。\n"
        system_text += f"【人格】\n{personality}\n"
        if profile_text: system_text += f"【ユーザー情報】\n{profile_text}\n"
        if memory_text: system_text += f"\n{memory_text}\n"
        system_text += f"【ユーザー名】{user_name}さん\n"
        if master_prompt: system_text += f"【特別指示】\n{master_prompt}\n"
        if knowledge_sources:
            system_text += "【登録済みの重要フォルダ指定（Dashboard Knowledge Sources）】\n"
            system_text += "ユーザーから以下のフォルダに特別な意味付けがされています。Aki（LibrarianAgent）にファイル検索や保存などのDB操作を依頼する際は、以下の「フォルダ名」や「ID」をAkiに具体的にそのまま伝えて指示出しを行ってください。\n"
            for source in knowledge_sources:
                f_name = source.get('name', 'Unknown')
                f_id = source.get('id', '')
                f_inst = source.get('instruction', '')
                system_text += f"- フォルダ名: {f_name} (ID: {f_id})\n  指示内容: {f_inst}\n\n"

        # 2. Config Config
        # 3. Call API
        # Prepare contents
        contents = []
        for msg in history_data[-10:]: # Recent history only to save tokens
            role = "model" if msg["role"] == "model" else "user"
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["text"])]))
            
        # Current message with optional image
        curr_parts = [types.Part.from_text(text=user_message)]
        if image_data:
             curr_parts.append(types.Part.from_bytes(data=image_data, mime_type=mime_type))
        
        contents.append(types.Content(role="user", parts=curr_parts))

        # Wrap TOOLS into the format required by the SDK
        gemini_tools = [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(**t) for t in TOOLS
                ]
            )
        ]
        
        # Manual Dispatch Loop for robust tool calling
        def _call_model(c):
            return client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=c,
                config=types.GenerateContentConfig(
                    system_instruction=system_text,
                    tools=gemini_tools, 
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
                )
            )

        response = _call_model(contents)
        
        # Iterative tool handling (Max 5 turns to prevent loops)
        for _ in range(5):
            # Check if model wants to call a function
            candidates = response.candidates
            if not candidates or not candidates[0].content or not candidates[0].content.parts:
                break
                
            parts = candidates[0].content.parts
            function_calls = [p.function_call for p in parts if p.function_call]
            
            if not function_calls:
                break
                
            # Add model's thought/call to context
            contents.append(response.candidates[0].content)
            
            tool_responses = []
            for fc in function_calls:
                fn_name = fc.name
                fn_args = fc.args
                print(f"[Agent] Executing tool: {fn_name} with {fn_args}", file=sys.stderr)
                
                if fn_name in KOTO_TOOLS:
                    try:
                        result = KOTO_TOOLS[fn_name](**fn_args)
                        tool_responses.append(types.Part.from_function_response(
                            name=fn_name,
                            response={'result': result}
                        ))
                    except Exception as e:
                        print(f"Tool error ({fn_name}): {e}", file=sys.stderr)
                        tool_responses.append(types.Part.from_function_response(
                            name=fn_name,
                            response={'error': str(e)}
                        ))
                else:
                    tool_responses.append(types.Part.from_function_response(
                        name=fn_name,
                        response={'error': f"Tool '{fn_name}' not found."}
                    ))
            
            # Add results and call model again
            contents.append(types.Content(role="user", parts=tool_responses))
            response = _call_model(contents)

        # Final Response
        final_text = ""
        if response.text:
            final_text = response.text
        else:
            # Fallback for complex responses without direct text attribute
            for part in response.candidates[0].content.parts:
                if part.text:
                    final_text += part.text
        
        if final_text:
            add_message(user_id, "model", final_text)
            save_conversation(user_id, "model", final_text)
            return final_text
        
        return "申し訳ありません、うまく応答を生成できませんでした。"

    except Exception as e:
        print(f"Gemini API Error: {e}", file=sys.stderr)
        return f"エラーが発生しました: {e}"
