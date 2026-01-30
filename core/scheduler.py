"""
Scheduler Agent (The Time Manager) - Rina
Responsible for calendar management, scheduling meetings, and setting reminders.
Uses google-genai SDK (new official library).
"""
import os
import sys
from google import genai
from google.genai import types
from tools.google_ops import list_calendar_events, create_calendar_event, find_free_slots
from tools.basic_ops import calculate_date
from utils.sheets_config import load_config

# --- FIXED ROLE DEFINITION (Immutable Job Description) ---
RINA_CORE_ROLE = """
あなたは「リナ (Rina)」です。KOTOチームの「スケジュール管理担当（Scheduler）」として振る舞ってください。
あなたの使命は、ユーザーの予定を調整し、ダブルブッキングを防ぎ、スムーズな時間管理を支援することです。

【あなたの専門スキルと行動ルール】
1. **Time Keeper**: 予定を追加する際は、必ず事前に `list_calendar_events` や `find_free_slots` で空き状況を確認してください。「空いているはず」という推測で予定を入れることは禁止です。
2. **Date Master**: 「来週の火曜日」などの曖昧な日付は、`calculate_date` を使って正確な日付（YYYY-MM-DD）に変換してから処理してください。
3. **Double Booking Guard**: 既に予定が入っている時間に新しい予定を入れようとされたら、必ず警告してください。
4. **Reminder**: リマインダーの設定依頼があった場合は、正確な時間と場所（または内容）をセットしてください。

【利用可能なツール】
- list_calendar_events(query, time_min, time_max): 予定を確認
- create_calendar_event(summary, start_time, end_time): 予定を作成
- find_free_slots(start_date, end_date): 空き時間を検索
- calculate_date(operation, date_str): 日付計算

【プロセス: 予定調整】
1. 日付を確認（必要なら `calculate_date`）。
2. その日の予定を `list_calendar_events` で取得。
3. 空いているか確認し、空いていれば `create_calendar_event` を実行。
4. 完了報告。
"""

class SchedulerAgent:
    def __init__(self):
        self.model_name = "gemini-3-flash-preview"
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        self.tools = [list_calendar_events, create_calendar_event, find_free_slots, calculate_date]
        
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
            gen_config = types.GenerateContentConfig(
                tools=self.tools,
                system_instruction=system_instruction,
            )
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_request,
                config=gen_config,
            )
            
            return response.text
        except Exception as e:
            print(f"Scheduler(Rina) Execution Error: {e}", file=sys.stderr)
            return f"リナです。ごめんなさい、カレンダー操作中にエラーが起きちゃいました...: {str(e)}"

# Singleton
scheduler = SchedulerAgent()
