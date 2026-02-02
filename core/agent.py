"""
Gemini AI Agent - handles conversation with Gemini API and tool execution
Uses google-genai SDK (new official library with automatic function calling).
"""
import os
import sys
import json
import datetime
import base64

from google import genai
from google.genai import types

from core.prompts import BASE_SYSTEM_PROMPT
from utils.storage import get_user_history, add_message

# Gemini API
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

# Current user ID for tools that need it
_current_user_id = None


def analyze_document_layout(image_data: bytes, mime_type: str) -> dict:
    """
    Analyze the visual layout and structure of a document image.
    Returns structured JSON data that can be used to recreate the document faithfully.
    
    Args:
        image_data: Image bytes
        mime_type: MIME type of the image
        
    Returns:
        Dictionary with document structure analysis
    """
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        analysis_prompt = """この画像を詳細に分析し、ドキュメントの構造を以下のJSON形式で出力してください。
できるだけ正確にレイアウトを再現できるよう、詳細に記述してください。

```json
{
  "document_type": "領収書/請求書/議事録/その他",
  "overall_layout": {
    "has_border": true/false,
    "has_header": true/false,
    "has_footer": true/false,
    "columns": 1,
    "text_alignment": "left/center/right"
  },
  "title": {
    "text": "タイトルテキスト",
    "position": "top-center/top-left/top-right",
    "style": "bold/normal",
    "size": "large/medium/small"
  },
  "sections": [
    {
      "type": "header/body/table/signature/footer",
      "position": "left/center/right",
      "content": [
        {"label": "ラベル", "value": "値", "style": "bold/normal"}
      ]
    }
  ],
  "special_elements": {
    "logo": true/false,
    "stamp": true/false,
    "signature_line": true/false,
    "date_field": {"position": "位置", "format": "YYYY年MM月DD日など"}
  },
  "styling_notes": "その他の重要なスタイリング情報（色、フォント、余白など）"
}
```

重要: 
- 各フィールドの正確なテキスト内容を含めてください
- 位置関係（左寄せ、中央、右寄せ）を正確に記述してください
- 罫線、表、区切り線の有無を明記してください
- 金額や日付のフォーマットを正確に記述してください"""

        # Create content with image
        content = [
            types.Part.from_bytes(data=image_data, mime_type=mime_type),
            analysis_prompt
        ]
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",  # Use stable model for analysis
            contents=content,
        )
        
        result_text = response.text
        
        # Try to extract JSON from the response
        import re
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', result_text)
        if json_match:
            json_str = json_match.group(1)
            try:
                structure = json.loads(json_str)
                return {"success": True, "structure": structure, "raw": result_text}
            except json.JSONDecodeError:
                pass
        
        # If no valid JSON, return the raw analysis
        return {"success": True, "structure": None, "raw": result_text}
        
    except Exception as e:
        print(f"Document layout analysis error: {e}", file=sys.stderr)
        return {"error": str(e)}

# --- Tool Wrapper Functions ---
# These are designed to be passed directly to the new SDK.
# Type hints and docstrings are crucial for the SDK to understand the tools.

def calculate(expression: str) -> dict:
    """Calculate a mathematical expression.
    
    Args:
        expression: Mathematical expression to calculate (e.g., "2+2", "sin(45)")
    
    Returns:
        Dictionary with expression and result
    """
    from tools.basic_ops import calculate as calc_impl
    return calc_impl(expression)

def calculate_date(operation: str, days: int = 0, date_str: str = None) -> dict:
    """Calculate dates. Get today's date, add/subtract days, or count days until a target.
    
    Args:
        operation: One of "today", "add", "until"
        days: Number of days to add (for "add" operation)
        date_str: Target date string YYYY-MM-DD (for "until" operation)
    
    Returns:
        Dictionary with date calculation result
    """
    from tools.basic_ops import calculate_date as calc_date_impl
    return calc_date_impl(operation, days, date_str)

def search_and_read_pdf(query: str) -> dict:
    """Search for PDFs in Google Drive and read their content.
    
    Args:
        query: Search query for finding PDFs
    
    Returns:
        Dictionary with PDF content
    """
    from tools.basic_ops import search_and_read_pdf as pdf_impl
    return pdf_impl(query)

def google_web_search(query: str, num_results: int = 5) -> dict:
    """Search the web using Google.
    
    Args:
        query: Search query
        num_results: Number of results to return (default 5)
    
    Returns:
        Dictionary with search results
    """
    from tools.web_ops import google_web_search as search_impl
    return search_impl(query, num_results)

def get_current_weather(location_name: str = "Tokyo") -> dict:
    """Get current weather for a location.
    
    Args:
        location_name: City name (default Tokyo)
    
    Returns:
        Dictionary with weather information
    """
    from tools.weather import get_current_weather as weather_impl
    return weather_impl(location_name)

def fetch_url(url: str) -> dict:
    """Fetch content from a URL.
    
    Args:
        url: URL to fetch
    
    Returns:
        Dictionary with page content
    """
    from tools.web_ops import fetch_url as fetch_impl
    return fetch_impl(url)

def create_google_doc(title: str, content: str = "") -> dict:
    """Create a new Google Document.
    
    Args:
        title: Document title
        content: Initial content (optional)
    
    Returns:
        Dictionary with document URL
    """
    from tools.google_ops import create_google_doc as doc_impl
    return doc_impl(title, content)

def create_google_sheet(title: str) -> dict:
    """Create a new Google Spreadsheet.
    
    Args:
        title: Spreadsheet title
    
    Returns:
        Dictionary with spreadsheet URL
    """
    from tools.google_ops import create_google_sheet as sheet_impl
    return sheet_impl(title)

def create_google_slide(title: str) -> dict:
    """Create a new Google Slides presentation.
    
    Args:
        title: Presentation title
    
    Returns:
        Dictionary with presentation URL
    """
    from tools.google_ops import create_google_slide as slide_impl
    return slide_impl(title)

def create_drive_folder(folder_name: str) -> dict:
    """Create a new folder in Google Drive.
    
    Args:
        folder_name: Name of the folder to create
    
    Returns:
        Dictionary with folder information
    """
    from tools.google_ops import create_drive_folder as folder_impl
    return folder_impl(folder_name)

def move_drive_file(file_id: str, folder_id: str) -> dict:
    """Move a file to a different folder in Google Drive.
    
    Args:
        file_id: ID of the file to move
        folder_id: ID of the destination folder
    
    Returns:
        Dictionary with move result
    """
    from tools.google_ops import move_drive_file as move_impl
    return move_impl(file_id, folder_id)

def search_drive(query: str) -> dict:
    """Search for files in Google Drive.
    
    Args:
        query: Search query
    
    Returns:
        Dictionary with found files
    """
    from tools.google_ops import search_drive as drive_impl
    return drive_impl(query)

def list_gmail(query: str = "is:unread", max_results: int = 5) -> dict:
    """List emails from Gmail.
    
    Args:
        query: Gmail search query (default "is:unread")
        max_results: Maximum number of results (default 5)
    
    Returns:
        Dictionary with email list
    """
    from tools.google_ops import list_gmail as gmail_impl
    return gmail_impl(query, max_results)

def get_gmail_body(message_id: str) -> dict:
    """Get the full body of an email.
    
    Args:
        message_id: Gmail message ID
    
    Returns:
        Dictionary with email body
    """
    from tools.google_ops import get_gmail_body as body_impl
    return body_impl(message_id)

def list_calendar_events(query: str = None, time_min: str = None, time_max: str = None) -> dict:
    """List calendar events.
    
    Args:
        query: Optional search query
        time_min: Start time (ISO format, e.g., "2024-01-01T00:00:00Z")
        time_max: End time (ISO format)
    
    Returns:
        Dictionary with calendar events
    """
    from tools.google_ops import list_calendar_events as cal_impl
    return cal_impl(query, time_min, time_max)

def create_calendar_event(summary: str, start_time: str, end_time: str, location: str = None) -> dict:
    """Create a new calendar event.
    
    Args:
        summary: Event title
        start_time: Start time (ISO format)
        end_time: End time (ISO format)
        location: Event location (optional)
    
    Returns:
        Dictionary with created event info
    """
    from tools.google_ops import create_calendar_event as create_impl
    return create_impl(summary, start_time, end_time, location)

def find_free_slots(start_date: str, end_date: str, duration: int = 60) -> dict:
    """Find available time slots in the calendar.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        duration: Slot duration in minutes (default 60)
    
    Returns:
        Dictionary with available slots
    """
    from tools.google_ops import find_free_slots as slots_impl
    return slots_impl(start_date, end_date, duration)

def list_tasks(show_completed: bool = False, due_date: str = None) -> dict:
    """List tasks from Google Tasks.
    
    Args:
        show_completed: Whether to include completed tasks
        due_date: Filter by due date (YYYY-MM-DD)
    
    Returns:
        Dictionary with task list
    """
    from tools.google_ops import list_tasks as tasks_impl
    return tasks_impl(show_completed, due_date)

def add_task(title: str, due_date: str = None) -> dict:
    """Add a new task to Google Tasks.
    
    Args:
        title: Task title
        due_date: Due date (YYYY-MM-DD, optional)
    
    Returns:
        Dictionary with created task info
    """
    from tools.google_ops import add_task as add_impl
    return add_impl(title, due_date)

def get_notion_tasks(filter_today_only: bool) -> dict:
    """Get tasks from the configured Notion database.
    
    Args:
        filter_today_only: If true, show only today's tasks. If false, show all tasks.
    
    Returns:
        Dictionary with task list
    """
    from tools.notion_ops import list_notion_tasks as notion_impl
    from utils.sheets_config import load_config
    
    config = load_config()
    notion_dbs = config.get("notion_databases", [])
    database_id = notion_dbs[0].get("id", "") if notion_dbs else ""
    
    if not database_id:
        return {"error": "Notionデータベースが設定されていません。管理コンソールでデータベースIDを追加してください。"}
    
    print(f"Notion: Using database_id={database_id}", file=sys.stderr)
    return notion_impl(database_id, filter_today_only)

def add_notion_task(title: str, due_date: str) -> dict:
    """Create a new task in the configured Notion database.
    
    Args:
        title: Task title (required)
        due_date: Due date in YYYY-MM-DD format (use empty string if no due date)
    
    Returns:
        Dictionary with created task info
    """
    from tools.notion_ops import create_notion_task as create_impl
    from utils.sheets_config import load_config
    
    config = load_config()
    notion_dbs = config.get("notion_databases", [])
    database_id = notion_dbs[0].get("id", "") if notion_dbs else ""
    
    if not database_id:
        return {"error": "Notionデータベースが設定されていません。管理コンソールでデータベースIDを追加してください。"}
    
    print(f"Notion: Creating task in database_id={database_id}", file=sys.stderr)
    return create_impl(database_id, title, due_date if due_date else None, None)

def complete_notion_task(page_id: str, new_status: str) -> dict:
    """Update the status of an existing Notion task.
    
    Args:
        page_id: Notion page ID of the task to update
        new_status: New status value (e.g., "完了", "Done")
    
    Returns:
        Dictionary with update result
    """
    from tools.notion_ops import update_notion_task as update_impl
    return update_impl(page_id, new_status, None)

def consult_fumi(request: str) -> dict:
    """Consult Fumi (資料作成担当) for document creation tasks. Use for creating docs, sheets, slides.
    
    Args:
        request: What you want Fumi to create or do
    
    Returns:
        Dictionary with Fumi's response
    """
    from core.maker import maker
    response_text = maker.run(request)
    return {"expert": "Fumi", "response": response_text}

def consult_aki(request: str) -> dict:
    """Consult Aki (司書担当) for file organization and search tasks. Use for finding or organizing files.
    
    Args:
        request: What you want Aki to find or organize
    
    Returns:
        Dictionary with Aki's response
    """
    from core.librarian import librarian
    response_text = librarian.run(request)
    return {"expert": "Aki", "response": response_text}

def consult_toki(request: str) -> dict:
    """Consult Toki (歴史担当) for past context and knowledge base lookups.
    
    Args:
        request: What information you want Toki to find
    
    Returns:
        Dictionary with Toki's response
    """
    from core.historian import historian
    response_text = historian.run(request)
    return {"expert": "Toki", "response": response_text}

def consult_ren(request: str) -> dict:
    """Consult Ren (広報担当) for drafting messages, emails, and communications.
    
    Args:
        request: What message you want Ren to draft
    
    Returns:
        Dictionary with Ren's response
    """
    from core.communicator import communicator
    response_text = communicator.run(request)
    return {"expert": "Ren", "response": response_text}

def consult_rina(request: str) -> dict:
    """Consult Rina (スケジュール担当) for calendar and scheduling tasks.
    
    Args:
        request: What scheduling task you want Rina to handle
    
    Returns:
        Dictionary with Rina's response
    """
    from core.scheduler import scheduler
    response_text = scheduler.run(request)
    return {"expert": "Rina", "response": response_text}

# Global user_id for set_reminder (needed for function context)
_current_user_id = None

def set_reminder(location: str) -> dict:
    """Set a daily weather reminder for a location.
    
    Args:
        location: Location name for weather reminders
    
    Returns:
        Dictionary with reminder setting result
    """
    global _current_user_id
    if not _current_user_id:
        return {"error": "ユーザーIDが取得できませんでした。"}
    from utils.user_db import register_user
    return register_user(_current_user_id, location)

def create_draft(body: str, to: str = None, subject: str = None) -> dict:
    """Create a draft email in Gmail.
    
    Args:
        body: Email body content
        to: Recipient email address (optional)
        subject: Email subject (optional)
        
    Returns:
        Dictionary with draft status
    """
    from tools.google_ops import create_gmail_draft
    return create_gmail_draft(to, subject, body)

def get_recent_uploads(count: int = 5) -> dict:
    """Get the most recently uploaded files from LINE.
    
    Args:
        count: Number of files to retrieve (default 5)
        
    Returns:
        Dictionary with list of recent files
    """
    from tools.google_ops import get_latest_uploads
    return get_latest_uploads(count)

def list_available_templates() -> dict:
    """List all templates in the template folder.
    
    Returns:
        Dictionary with list of templates
    """
    from tools.template_ops import list_templates
    return list_templates()

def check_new_templates() -> dict:
    """Check for new templates that haven't been registered yet.
    
    Returns:
        Dictionary with unregistered templates that need user input
    """
    from tools.template_ops import check_unregistered_templates
    return check_unregistered_templates()

def find_template(template_type: str) -> dict:
    """Find a registered template by type or name.
    
    Args:
        template_type: Type to search for (e.g., "領収書", "議事録")
        
    Returns:
        Dictionary with matching template
    """
    from tools.template_ops import find_template_by_type
    return find_template_by_type(template_type)

def use_template(template_type: str, new_document_name: str) -> dict:
    """Use a template to create a new document.
    
    Args:
        template_type: Type of template to use (e.g., "領収書")
        new_document_name: Name for the new document
        
    Returns:
        Dictionary with new document info
    """
    from tools.template_ops import find_template_by_type, copy_template
    
    # First find the template
    result = find_template_by_type(template_type)
    if result.get("error"):
        return result
    if not result.get("found"):
        return {"error": f"「{template_type}」のテンプレートが見つかりませんでした。「テンプレート一覧」で確認してください。"}
    
    template = result["template"]
    
    # Copy the template
    copy_result = copy_template(template["file_id"], new_document_name)
    if copy_result.get("error"):
        return copy_result
    
    return {
        "success": True,
        "message": f"テンプレート「{template['name']}」を使用して「{new_document_name}」を作成しました。",
        "url": copy_result.get("url"),
        "file_id": copy_result.get("file_id"),
        "template_fields": template.get("fields", []),
        "hint": "このドキュメントを開いて、必要な項目を埋めてください。"
    }

def register_new_template(file_id: str, name: str, template_type: str, description: str, fields: str, usage_hint: str) -> dict:
    """Register a new template in the registry.
    
    Args:
        file_id: Google Drive file ID of the template
        name: Template name
        template_type: Type (領収書, 議事録, etc.)
        description: What this template is for
        fields: Comma-separated list of fields to fill
        usage_hint: When to use this template
        
    Returns:
        Dictionary with registration result
    """
    from tools.template_ops import register_template
    fields_list = [f.strip() for f in fields.split(',')] if fields else []
    return register_template(file_id, name, template_type, description, fields_list, usage_hint)

# All available tools for Koto
KOTO_TOOLS = [
    calculate,
    calculate_date,
    search_and_read_pdf,
    google_web_search,
    get_current_weather,
    fetch_url,
    create_google_doc,
    create_google_sheet,
    create_google_slide,
    create_drive_folder,
    move_drive_file,
    search_drive,
    list_gmail,
    get_gmail_body,
    create_draft,
    get_recent_uploads,
    list_calendar_events,
    create_calendar_event,
    find_free_slots,
    list_tasks,
    add_task,
    get_notion_tasks,
    add_notion_task,
    complete_notion_task,
    set_reminder,
    consult_fumi,
    consult_aki,
    consult_toki,
    consult_ren,
    consult_rina,
    list_available_templates,
    check_new_templates,
    find_template,
    use_template,
    register_new_template,
]


def get_gemini_response(user_id, user_message, image_data=None, mime_type=None):
    """Get response from Gemini API using the new google-genai SDK with automatic function calling."""
    global _current_user_id
    _current_user_id = user_id  # Set for set_reminder tool
    
    if not GEMINI_API_KEY:
        return "APIキーが設定されていません〜"
    
    # Add user message to history
    log_message = user_message
    if image_data:
        log_message += " [添付画像あり]"
    add_message(user_id, "user", log_message)
    
    # Get conversation history
    history = get_user_history(user_id)
    
    # Build dynamic system prompt with config-based customizations
    from utils.sheets_config import load_config
    try:
        config = load_config()
    except:
        config = {}
    
    # Get personality and master prompt
    personality = config.get("koto_personality") or config.get("personality", "明るくて元気なAI秘書")
    master_prompt = config.get("koto_master_prompt") or config.get("master_prompt", "")
    
    personality_section = f"\n【設定された人格・役割（KOTO）】\n{personality}\n"
    master_prompt_section = f"\n【マスタープロンプト（特別指示）】\n{master_prompt}\n" if master_prompt else ""
    
    # Current Date/Time context (CRITICAL for model awareness)
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S (%A)')
    time_context = f"\n【★現在日時★】\n本日は {now_str} です。ユーザーから「今日」「明日」と言われたらこの日付を基準にしてください。\n"
    
    # User Context (Profile)
    from utils.vector_store import get_user_profile
    user_data = get_user_profile(user_id)
    profile_text = user_data.get('profile', '') if isinstance(user_data, dict) else ''
    profile_section = f"\n【ユーザープロファイル（過去の分析結果）】\n{profile_text}\n" if profile_text else ""
    
    user_name = config.get('user_name', 'ユーザー')
    user_name_section = f"\n【ユーザーの名前】\n{user_name}さん\n"
    
    # Assemble Full System Prompt
    full_system_prompt = BASE_SYSTEM_PROMPT + time_context + personality_section + profile_section + user_name_section + master_prompt_section
    
    # Initialize the new SDK client
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    try:
        # Configure generation with tools and system instruction
        gen_config = types.GenerateContentConfig(
            tools=KOTO_TOOLS,
            system_instruction=full_system_prompt,
            temperature=0.8,
            max_output_tokens=2048,
        )
        
        # Build contents (history + current message)
        contents = []
        
        # Add history
        for msg in history:
            role = "model" if msg["role"] == "model" else "user"
            contents.append(types.Content(
                role=role,
                parts=[types.Part.from_text(text=msg["text"])]
            ))
        
        # Add current message (with image if present)
        current_parts = []
        if image_data and mime_type:
            current_parts.append(types.Part.from_bytes(data=image_data, mime_type=mime_type))
        current_parts.append(types.Part.from_text(text=user_message))
        contents.append(types.Content(role="user", parts=current_parts))
        
        # Generate response with automatic function calling
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=contents,
            config=gen_config,
        )
        
        # Extract text response
        response_text = response.text if hasattr(response, 'text') else str(response)
        
        # Log response
        add_message(user_id, "model", response_text)
        
        # Save to vector store
        try:
            from utils.vector_store import save_conversation
            save_conversation(user_id, "user", user_message)
            save_conversation(user_id, "model", response_text)
        except:
            pass
        
        return response_text
        
    except Exception as e:
        print(f"Gemini SDK error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return f"ちょっとエラーが出ちゃいました...😢\nDEBUG: {str(e)}"
