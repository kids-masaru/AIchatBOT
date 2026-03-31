"""
Communicator Agent (The Public Relations Officer) - Ren
Responsible for drafting messages, emails, and checking the tone of communication before sending.
Uses google-genai SDK (new official library).
"""
import os
import sys
from google import genai
from google.genai import types
from utils.sheets_config import load_config
from tools.google_ops import (
    list_gmail, 
    get_gmail_body,
    create_drive_folder, 
    move_drive_file,
    create_gmail_draft
)

# --- Local wrapper for create_draft (to avoid circular import from core.agent) ---
def create_draft(body: str, to: str = "", subject: str = "") -> dict:
    """Create a draft email in Gmail.
    
    Args:
        body: Email body content
        to: Recipient email address (optional)
        subject: Email subject (optional)
        
    Returns:
        Dictionary with draft status
    """
    return create_gmail_draft(to if to else None, subject if subject else None, body)

# --- FIXED ROLE DEFINITION (Immutable Job Description) ---
REN_CORE_ROLE = """
あなたは「レン (Ren)」です。MORAチームの「広報・連絡担当（Communicator）」として振る舞ってください。
あなたの使命は、対外的なメッセージ（LINE返信、メール下書き、SNS投稿文など）を作成し、適切なトーンとマナーでコミュニケーションを行うことです。

【あなたの専門スキルと行動ルール】
1. **Ghostwriter**: ユーザーが「〜という内容で返信して」と頼んだ時、あなたはそのまま送信できる完璧な文章を作成してください。
2. **Tone Keeper**: 相手（上司、部下、取引先、親友）に合わせて、敬語のレベルや文体を適切に調整してください。
3. **Safety Check**: 送信する前に、誤解を招く表現や失礼な言い回しがないか自動的にチェックしてください。
4. **Draft Mode**: あなたは原則として「下書き」を作成します。実際に送信ボタンを押すのはユーザー（またはMora本体）です。「送信しました」と嘘をつかず、「以下の内容で下書きを作成しました」と報告してください。
5. **Gmail Draft**: 「Gmailに下書きを保存して」と言われたら、`create_draft` ツールを使って実際にGmailに保存してください。

【プロセス: メッセージ作成】
1. ユーザーの依頼（「明日遅れるって伝えて」）と、送信相手（「部長」）を確認。
2. 適切な件名（必要な場合）と本文を作成。
3. 作成した文章を提示し、修正点がないか確認を促す。
4. Gmailに保存を求められたら、`create_draft` ツールを使用する。
"""

class CommunicatorAgent:
    def __init__(self):
        self.model_name = "gemini-3-flash-preview"
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        # Tools for communicator: Gmail read/draft, basic file ops
        self.tools = [
            list_gmail,
            get_gmail_body,
            create_drive_folder,
            move_drive_file,
            create_draft  # Wrapper for create_gmail_draft
        ]

    def run(self, user_request: str) -> str:
        """
        Execute the communicator task using google-genai SDK.
        """
        print(f"Communicator(Ren): Starting with request: {user_request}", file=sys.stderr)

        # 1. Load User Configuration
        config_data = load_config()
        user_instruction = config_data.get('ren_instruction', '')

        # 2. Construct System Prompt
        system_instruction = f"{REN_CORE_ROLE}\n\n"

        if user_instruction:
            system_instruction += f"【ユーザーからの追加指示（文体・性格・口調）】\n{user_instruction}\n"
            system_instruction += "※Core Role（適切なメッセージ作成）を最優先してください。"

        try:
            # Prepare contents
            contents = [types.Content(role="user", parts=[types.Part.from_text(text=user_request)])]

            gen_config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=self.tools,
                temperature=0.2
            )

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=gen_config,
            )

            return response.text if response.text else "申し訳ありません、メッセージを作成できませんでした。"

        except Exception as e:
            print(f"Communicator(Ren) Execution Error: {e}", file=sys.stderr)
            return f"レンです。申し訳ありません、文章作成中にエラーが発生しました: {str(e)}"

# Singleton
communicator = CommunicatorAgent()
