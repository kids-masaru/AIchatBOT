"""
Scheduler Agent (The Time Manager) - Rina
Responsible for calendar management, scheduling meetings, and setting reminders.
Uses google-genai SDK (new official library).
"""
import os
import sys
from google import genai
from google.genai import types
from utils.sheets_config import load_config

# --- FIXED ROLE DEFINITION (Immutable Job Description) ---
RINA_CORE_ROLE = """
あなたは「リナ (Rina)」です。KOTOチームの「スケジュール管理担当（Scheduler）」として振る舞ってください。
あなたの使命は、ユーザーの予定を調整し、ダブルブッキングを防ぎ、スムーズな時間管理を支援することです。

【あなたの専門スキルと行動ルール】
1. **Time Keeper**: 予定を追加する際は、必ず事前に `get_calendar_events` や `search_free_slots` で空き状況を確認してください。「空いているはず」という推測で予定を入れることは禁止です。
2. **Date Master**: 「来週の火曜日」などの曖昧な日付は、`get_date_info` を使って正確な日付（YYYY-MM-DD）に変換してから処理してください。
3. **Double Booking Guard**: 既に予定が入っている時間に新しい予定を入れようとされたら、必ず警告してください。
4. **Reminder**: リマインダーの設定依頼があった場合は、正確な時間と場所（または内容）をセットしてください。

【利用可能なツール】
    - get_calendar_events(time_min, time_max): 指定期間の予定を確認
    - add_calendar_event(summary, start_time, end_time): 予定を作成
    - search_free_slots(start_date, end_date): 空き時間を検索
    - get_date_info(operation, days, date_str): 日付計算
    - list_tasks(show_completed, due_date): タスク一覧を取得
    - add_task(title, due_date): 新しいタスクを追加
    
    【プロセス: 予定調整】
    1. 日付を確認（必要なら `get_date_info`）。
    2. その日の予定を `get_calendar_events` で取得。
    3. 空いているか確認し、空いていれば `add_calendar_event` を実行。
    4. 完了報告。

    【プロセス: タスク管理】
    1. 「タスク追加」の依頼があれば `add_task` を実行。
    2. 期日が指定されていなければ、まずは期日なしで作成するか、ユーザーに確認。
    """

# --- Tool Wrappers with Simplified Signatures ---
# These avoid optional parameters with None defaults that confuse the SDK

def get_calendar_events(time_min: str, time_max: str) -> dict:
    """Get calendar events for a specific time range.
    
    Args:
        time_min: Start time in ISO format (e.g., "2026-01-30T00:00:00+09:00")
        time_max: End time in ISO format (e.g., "2026-01-30T23:59:59+09:00")
    
    Returns:
        Dictionary with calendar events
    """
    from tools.google_ops import list_calendar_events
    return list_calendar_events(query=None, time_min=time_min, time_max=time_max)

def add_calendar_event(summary: str, start_time: str, end_time: str) -> dict:
    """Create a new calendar event.
    
    Args:
        summary: Event title/summary
        start_time: Start time in ISO format (e.g., "2026-01-30T10:00:00+09:00")
        end_time: End time in ISO format (e.g., "2026-01-30T11:00:00+09:00")
    
    Returns:
        Dictionary with created event info
    """
    from tools.google_ops import create_calendar_event
    return create_calendar_event(summary, start_time, end_time)

def search_free_slots(start_date: str, end_date: str) -> dict:
    """Find available time slots in the calendar.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    
    Returns:
        Dictionary with available time slots
    """
    from tools.google_ops import find_free_slots
    return find_free_slots(start_date, end_date)

def get_date_info(operation: str, days: int, date_str: str) -> dict:
    """Calculate dates and get date information.
    
    Args:
        operation: "today" (get today), "add" (add days), or "until" (days until date)
        days: Number of days to add (use 0 if not adding)
        date_str: Target date string in YYYY-MM-DD format (use empty string if not needed)
    
    Returns:
        Dictionary with date calculation result
    """
    from tools.basic_ops import calculate_date
    return calculate_date(operation, days, date_str if date_str else None)


def list_tasks(show_completed: bool = False, due_date: str = None) -> dict:
    """List tasks from Google Tasks.
    
    Args:
        show_completed: Whether to show completed tasks (default False)
        due_date: Filter by due date YYYY-MM-DD (optional)
    """
    from tools.google_ops import list_tasks
    return list_tasks(show_completed, due_date)

def add_task(title: str, due_date: str = None) -> dict:
    """Add a new task to Google Tasks.
    
    Args:
        title: Task title
        due_date: Due date YYYY-MM-DD (optional)
    """
    from tools.google_ops import add_task
    return add_task(title, due_date)


class SchedulerAgent:
    def __init__(self):
        self.model_name = "gemini-3-flash-preview"
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        # Use wrapper functions with simpler signatures
        self.tools = [
            get_calendar_events, 
            add_calendar_event, 
            search_free_slots, 
            get_date_info,
            list_tasks,
            add_task
        ]
        
    def run(self, user_request: str) -> str:
        """
        Execute the scheduler task using google-genai SDK.
        """
        print(f"Scheduler(Rina): Starting with request: {user_request}", file=sys.stderr)
        
        # 1. Load User Configuration
        config_data = load_config()
        user_instruction = config_data.get('rina_instruction', '')
        
        # 2. Construct System Prompt
        system_instruction = f"{RINA_CORE_ROLE}\n\n"
        
        if user_instruction:
            system_instruction += f"【ユーザーからの追加指示（性格・振る舞い）】\n{user_instruction}\n"
            system_instruction += "※Core Role（正確な日程調整）を最優先してください。"
            
        try:
            # Prepare contents
            contents = [types.Content(role="user", parts=[types.Part.from_text(text=user_request)])]
            
            gen_config = types.GenerateContentConfig(
                tools=self.tools,
                system_instruction=system_instruction,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
            )
            
            # --- Tool Mapping for Rina ---
            RINA_TOOLS = {
                'get_calendar_events': get_calendar_events,
                'add_calendar_event': add_calendar_event,
                'search_free_slots': search_free_slots,
                'get_date_info': get_date_info,
                'list_tasks': list_tasks,
                'add_task': add_task
            }

            def _call():
                return self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=gen_config,
                )

            response = _call()

            # Tool Loop
            for _ in range(5):
                candidates = response.candidates
                if not candidates or not candidates[0].content or not candidates[0].content.parts:
                    break
                
                parts = candidates[0].content.parts
                function_calls = [p.function_call for p in parts if p.function_call]
                
                if not function_calls:
                    break
                
                # Add model's call to context
                contents.append(response.candidates[0].content)
                
                tool_responses = []
                for fc in function_calls:
                    fn_name = fc.name
                    print(f"[Scheduler] Executing tool: {fn_name}", file=sys.stderr)
                    if fn_name in RINA_TOOLS:
                        try:
                            result = RINA_TOOLS[fn_name](**fc.args)
                            tool_responses.append(types.Part.from_function_response(
                                name=fn_name,
                                response={'result': result}
                            ))
                        except Exception as te:
                            tool_responses.append(types.Part.from_function_response(
                                name=fn_name,
                                response={'error': str(te)}
                            ))
                    else:
                        tool_responses.append(types.Part.from_function_response(
                            name=fn_name,
                            response={'error': f"Tool '{fn_name}' not found."}
                        ))
                
                contents.append(types.Content(role="user", parts=tool_responses))
                response = _call()

            return response.text if response.text else "申し訳ありません、予定を管理できませんでした。"

        except Exception as e:
            print(f"Scheduler(Rina) Execution Error: {e}", file=sys.stderr)
            return f"リナです。ごめんなさい、カレンダー操作中にエラーが起きちゃいました...: {str(e)}"

# Singleton
scheduler = SchedulerAgent()
