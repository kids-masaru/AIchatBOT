"""
Mora Agent - AI Logic (Gemini API Version)
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
from tools.notion_ops import (
    list_notion_tasks, create_notion_task, update_notion_task, 
    toggle_notion_checkbox, get_notion_db_schema, update_notion_task_properties
)
from tools.template_ops import (
    list_templates, check_unregistered_templates, find_template_by_type,
    copy_template, register_template, replace_placeholders
)
from tools.knowledge_updater import update_common_knowledge


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


def _resolve_notion_db_id(client_config=None, database_name=None):
    """
    Helper to resolve a database name to an ID using the config.
    """
    from utils.sheets_config import load_config
    spreadsheet_id = client_config.get('spreadsheet_id') if client_config else None
    config = load_config(spreadsheet_id)
    dbs = config.get("notion_databases", [])
    
    if not dbs:
        return ""
        
    if not database_name:
        return dbs[0].get("id", "")
        
    # Try exact match
    for db in dbs:
        if db.get("name") == database_name:
            return db.get("id", "")
            
    # Try partial match
    for db in dbs:
        if database_name in db.get("name", ""):
            return db.get("id", "")
            
    return dbs[0].get("id", "")


def load_skill(skill_name: str, client_config=None) -> dict:
    """
    Find and load a skill (prompt) from the MORA_SKILLS folder.
    """
    from utils.sheets_config import load_config, save_config
    from tools.google_ops import search_drive, read_drive_file, create_drive_folder
    spreadsheet_id = client_config.get('spreadsheet_id') if client_config else None
    config = load_config(spreadsheet_id)
    folder_id = config.get("skills_folder_id")
    
    if not folder_id:
        # Try to find existing folder
        print(f"[Agent] Skills folder ID missing. Searching for 'MORA_SKILLS'...", file=sys.stderr)
        res = search_drive("MORA_SKILLS")
        folders = [f for f in res.get("files", []) if f.get("mimeType") == "application/vnd.google-apps.folder"]
        
        if folders:
            folder_id = folders[0]["id"]
        else:
            # Create if not found
            print(f"[Agent] Creating 'MORA_SKILLS' folder...", file=sys.stderr)
            new_folder = create_drive_folder("MORA_SKILLS")
            folder_id = new_folder.get("id")
            
        if folder_id:
            config["skills_folder_id"] = folder_id
            save_config(config)

    if not folder_id:
        return {"error": "スキルフォルダの取得に失敗しました。"}

    # Search for the skill file in that folder
    print(f"[Agent] Searching for skill '{skill_name}' in folder {folder_id}", file=sys.stderr)
    res = search_drive(skill_name, folder_id=folder_id)
    files = res.get("files", [])
    
    if not files:
        return {"error": f"スキル「{skill_name}」が見つかりませんでした。MORA_SKILLSフォルダ内にファイルを作成してください。"}
    
    # Read the first match
    file_id = files[0]["id"]
    content_res = read_drive_file(file_id)
    
    if content_res.get("success"):
        return {
            "success": True, 
            "skill_name": skill_name, 
            "instructions": content_res.get("content"),
            "source": files[0]["name"]
        }
    else:
        return {"error": f"スキル「{skill_name}」の読み込みに失敗しました。"}


def save_skill(skill_name: str, instructions: str, description: str = "", client_config=None) -> dict:
    """
    Save a new skill (prompt) to the MORA_SKILLS folder.
    """
    from utils.sheets_config import load_config, save_config
    from tools.google_ops import search_drive, create_drive_folder, create_google_doc
    spreadsheet_id = client_config.get('spreadsheet_id') if client_config else None
    config = load_config(spreadsheet_id)
    folder_id = config.get("skills_folder_id")
    
    # 1. Ensure folder exists (duplicated from load_skill for safety, should refactor later)
    if not folder_id:
        res = search_drive("MORA_SKILLS")
        folders = [f for f in res.get("files", []) if f.get("mimeType") == "application/vnd.google-apps.folder"]
        if folders:
            folder_id = folders[0]["id"]
        else:
            new_folder = create_drive_folder("MORA_SKILLS")
            folder_id = new_folder.get("id")
        if folder_id:
            config["skills_folder_id"] = folder_id
            save_config(config)

    if not folder_id:
        return {"error": "スキルフォルダの取得に失敗しました。"}

    # 2. Check if skill already exists
    res = search_drive(skill_name, folder_id=folder_id)
    files = res.get("files", [])
    
    # 3. Create or Update? For now, we always create or tell them to update? 
    # Let's just create a new one with a timestamp if conflict, or overwrite. 
    # Overwrite is cleaner for "Skills".
    
    # Prepend description if present
    content = f"【説明】\n{description}\n\n【指示内容】\n{instructions}" if description else instructions
    
    creation_res = create_google_doc(skill_name, content)
    if creation_res.get("success"):
        file_id = creation_res.get("file_id")
        # Move to skills folder
        from tools.google_ops import move_drive_file
        move_drive_file(file_id, folder_id)
        return {
            "success": True, 
            "message": f"スキル「{skill_name}」を保存しました。",
            "url": creation_res.get("url")
        }
    else:
        return {"error": f"スキル「{skill_name}」の保存に失敗しました。"}


# Map tool names to functions
MORA_TOOLS = {
    'calculate': calculate,
    'calculate_date': calculate_date,
    'search_drive': search_drive,
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
    'list_gmail': list_gmail,
    'get_gmail_body': get_gmail_body,
    'create_gmail_draft': create_gmail_draft,
    'get_latest_uploads': get_latest_uploads,
    'list_calendar_events': list_calendar_events,
    'create_calendar_event': create_calendar_event,
    'find_free_slots': find_free_slots,
    'list_tasks': list_tasks,
    'add_task': add_task,
    'search_notion': lambda query=None, database_id=None: list_notion_tasks(database_id or _resolve_notion_db_id(client_config)),
    'add_notion_task': lambda title, content=None, due_date=None, status=None, database_id=None: create_notion_task(database_id or _resolve_notion_db_id(client_config), title, due_date, status, content=content),
    'update_notion_task': update_notion_task,
    'get_notion_db_schema': get_notion_db_schema,
    'complete_notion_task': lambda page_id, new_status: update_notion_task(page_id, new_status, None),
    'toggle_notion_checkbox': lambda page_id, property_name, checked: toggle_notion_checkbox(page_id, property_name, checked),
    'update_notion_properties': lambda page_id, properties: update_notion_task_properties(page_id, properties),
    'set_reminder': set_reminder,
    'list_available_templates': list_templates,
    'check_new_templates': check_unregistered_templates,
    'find_template': find_template_by_type,
    'use_template': use_template,
    'register_new_template': register_new_template,
    'doc_replace_text': replace_placeholders,
    'update_agent_instruction': lambda agent_name, new_instruction: __import__('utils.sheets_config', fromlist=['update_agent_instruction']).update_agent_instruction(agent_name, new_instruction),
    'load_skill': lambda skill_name: load_skill(skill_name, client_config),
    'save_skill': lambda skill_name, instructions, description="": save_skill(skill_name, instructions, description, client_config),
    'update_common_knowledge': lambda fact, category="General": update_common_knowledge(fact, category, spreadsheet_id=client_config.get('spreadsheet_id') if client_config else None)
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


def get_gemini_response(user_id, user_message, image_data=None, mime_type=None, on_tool_call=None, client_config=None):
    """
    Main Agent Logic using Google Gemini API directly.
    """
    # T05: set_reminderをクロージャとして定義（グローバル変数不使用）
    def set_reminder(location: str) -> dict:
        from utils.user_db import register_user
        return register_user(user_id, location)


    if not GEMINI_API_KEY:
        return "エラー: GEMINI_API_KEYが設定されていません。"

    from utils.vector_store import save_conversation, get_user_profile, get_context_summary
    from utils.agent_log import is_debug_mode, set_debug_mode, add_log, format_log_for_line

    # Debug mode toggle detection
    msg_lower = user_message.strip().lower()
    if any(kw in user_message for kw in ["裏側見せて", "デバッグモード", "デバッグON", "デバッグオン"]):
        set_debug_mode(user_id, True)
    elif any(kw in user_message for kw in ["もう大丈夫", "デバッグオフ", "デバッグOFF", "裏側やめて"]):
        set_debug_mode(user_id, False)

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # 1. Build System Prompt & History
        # IMPORTANT: Load context summary BEFORE adding current message to history/vector store
        # to avoid self-referencing mirroring bugs.
        memory_text = get_context_summary(user_id, user_message)
        
        # Now safe to add to temporary history for the current request
        add_message(user_id, "user", user_message)
        # Fix RAG: Store user message into Pinecone as well to enable bidirectional memory retrieval
        save_conversation(user_id, "user", user_message)
        
        history_data = get_user_history(user_id)
        
        from utils.sheets_config import load_config
        spreadsheet_id = client_config.get('spreadsheet_id') if client_config else None
        config = load_config(spreadsheet_id)
        
        personality = config.get("mora_personality", "明るくて元気なAI秘書")
        master_prompt = config.get("mora_master_prompt", "")
        # Fix: Use JST explicitly (Railway runs in UTC)
        jst = datetime.timezone(datetime.timedelta(hours=9))
        now_str = datetime.datetime.now(jst).strftime('%Y-%m-%d %H:%M:%S (%A)')
        
        user_data = get_user_profile(user_id)
        # Safety: Profiler may rarely save a list instead of dict
        if not isinstance(user_data, dict):
            user_data = {}
        profile_text = user_data.get('profile', '')
        # If profile has no 'profile' key but has 'summary', use that
        if not profile_text and isinstance(user_data, dict):
            profile_text = user_data.get('summary', '')
            if not profile_text:
                # Use the whole profile dict as text
                profile_text = json.dumps(user_data, ensure_ascii=False)[:2000] if user_data else ''
        user_name = config.get('user_name', 'ユーザー')
        knowledge_sources = config.get('knowledge_sources', [])
        
        system_text = f"{BASE_SYSTEM_PROMPT}\n現在の時間は {now_str} です。\n"
        system_text += f"【人格】\n{personality}\n"
        if profile_text: system_text += f"【今回のユーザー情報（プライベート）】\n{profile_text}\n※この情報は今回の対話の文脈としてのみ使用し、他ユーザーと共有（共通知識化）しないでください。\n"
        if memory_text: system_text += f"\n【過去の関連知識・やり取り】\n{memory_text}\n"
        system_text += f"【ユーザー名】{user_name}さん\n"
        if master_prompt: system_text += f"【クライアント固有の特別指示】\n{master_prompt}\n"
        
        system_text += """
【知識の取り扱いルール】
1. **共通知識 (Tier A/B)**: 全ユーザーで共有すべき業務知識（マニュアル、FAQ、確定した業務ルールなど）は `update_common_knowledge` を使って記録してください。
2. **個人の文脈 (Tier C)**: ユーザーの個人的な悩み、予定、趣味などは、今回の会話の文脈としてのみ扱い、共通知識には書き込まないでください。
3. **仕事用ボットの徹底**: 「これは仕事用のツールです」という前提で振る舞い、過度にプライベートな話題には「仕事の範囲でお答えします」と丁寧に対応してください。
"""

        if knowledge_sources:
            system_text += "【登録済みの重要フォルダ指定（Dashboard Knowledge Sources）】\n"
            system_text += "ユーザーから以下のフォルダに特別な意味付けがされています。Aki（LibrarianAgent）にファイル検索や保存などのDB操作を依頼する際は、以下の「フォルダ名」や「ID」をAkiに具体的にそのまま伝えて指示出しを行ってください。\n"
            for source in knowledge_sources:
                if not isinstance(source, dict):
                    continue
                f_name = source.get('name', 'Unknown')
                f_id = source.get('id', '')
                f_inst = source.get('instruction', '')
                system_text += f"- フォルダ名: {f_name} (ID: {f_id})\n  指示内容: {f_inst}\n\n"

        notion_dbs = config.get('notion_databases', [])
        if notion_dbs:
            system_text += "【登録済みのNotionデータベース指定】\n"
            system_text += "ユーザーから以下のデータベースが管理コンソールに登録されています。操作対象のデータベースが明白な場合は、その「データベース名」を引数に指定してツールを実行してください。特定の指示がある場合はそれに従ってください。\n"
            for db in notion_dbs:
                if not isinstance(db, dict): continue
                db_name = db.get('name', 'Unknown')
                db_inst = db.get('instruction', '')
                system_text += f"- データベース名: {db_name}\n  指示内容: {db_inst}\n\n"

        # 2. Call API
        # Prepare contents from history
        contents = []
        
        for msg in history_data[:-1]: # Past history
            role = "model" if msg["role"] == "model" else "user"
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["text"])]))
            
        # Add current message (last one in history) with image if present
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
        
        gen_config = types.GenerateContentConfig(
            system_instruction=system_text,
            tools=gemini_tools,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            temperature=0.2
        )

        # Manual Tool Execution Loop
        # T05: リクエストごとにset_reminderクロージャを含むローカルツール辞書を生成
        local_tools = {**MORA_TOOLS, 'set_reminder': set_reminder}

        # FunctionDeclaration-based tools require manual dispatch via local_tools dict
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=contents,
            config=gen_config,
        )

        for _ in range(10):  # Max 10 tool rounds to prevent infinite loops
            # Check if the response contains function calls
            candidates = response.candidates
            if not candidates:
                break
            
            parts = candidates[0].content.parts
            function_calls = [p for p in parts if p.function_call]
            
            if not function_calls:
                break  # No more tool calls, exit loop
            
            # Execute each function call
            tool_responses = []
            for fc_part in function_calls:
                fn_name = fc_part.function_call.name
                fn_args = dict(fc_part.function_call.args) if fc_part.function_call.args else {}
                
                print(f"[Agent] Executing tool: {fn_name} with {fn_args}", file=sys.stderr)
                
                if fn_name in local_tools:
                    try:
                        result = local_tools[fn_name](**fn_args)
                    except Exception as tool_err:
                        result = {"error": f"Tool execution failed: {str(tool_err)}"}
                        print(f"[Agent] Tool error ({fn_name}): {tool_err}", file=sys.stderr)
                else:
                    result = {"error": f"Unknown tool: {fn_name}"}
                
                # Record to agent log
                add_log(user_id, fn_name, fn_args, result, round_num=_+1)
                
                # Debug mode: send to LINE via callback
                if on_tool_call and is_debug_mode(user_id):
                    try:
                        from utils.agent_log import get_session_logs
                        latest = get_session_logs(user_id)
                        if latest:
                            line_msg = format_log_for_line(latest[-1])
                            on_tool_call(user_id, line_msg)
                    except Exception as cb_err:
                        print(f"[Agent] Debug callback error: {cb_err}", file=sys.stderr)
                
                # Truncate large tool outputs to prevent token exhaustion
                result_str = json.dumps(result, ensure_ascii=False, default=str) if not isinstance(result, str) else result
                if len(result_str) > 15000:
                    result_str = result_str[:15000] + "...(truncated)"
                    result = {"truncated_result": result_str}
                
                tool_responses.append(
                    types.Part.from_function_response(
                        name=fn_name,
                        response={"result": result}
                    )
                )
            
            # Send tool results back to Gemini
            contents.append(candidates[0].content)  # AI's function_call turn
            contents.append(types.Content(role="user", parts=tool_responses))
            
            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=contents,
                config=gen_config,
            )
        
        # Extract final text response
        final_text = ""
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
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
        import traceback
        traceback.print_exc(file=sys.stderr)
        return f"エラーが発生しました: {e}"
