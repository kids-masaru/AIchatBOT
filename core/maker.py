"""
Maker Agent (The Writer)
Specialized in creating documents (Docs, Slides, Spreadsheets) by researching Google Drive.
"""
import os
import sys
import json
import google.generativeai as genai
from tools.google_ops import search_drive, read_drive_file, create_google_doc, create_google_sheet, create_google_slide, move_drive_file, create_drive_folder
from utils.sheets_config import load_config

class MakerAgent:
    def __init__(self):
        self.model_name = "gemini-2.0-flash-exp" # High reasoning capability
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            
        # Define the specific tools for this agent
        self.tools = [search_drive, read_drive_file, create_google_doc, create_google_sheet, create_google_slide, move_drive_file, create_drive_folder]
        
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            tools=self.tools
        )
        
    def run(self, user_request: str, chat_history: list = None) -> str:
        """
        Execute the maker task.
        In a real agentic loop, this would run multiple turns (Search -> Read -> Write).
        For now, we use Gemini's automatic function calling (if available in the library version) 
        or a simple ReAct loop. 
        Given the current simple implementation of `agent.py`, we'll try to use the model's auto-tool-use capability.
        """
        print(f"Maker: Starting with request: {user_request}", file=sys.stderr)
        
        config = load_config()
        # Allow user to customize the persona via config
        system_instruction = config.get('maker_prompt', """
        あなたは「フミ (Fumi)」です。資料作成の専門家として振る舞ってください。
        ユーザーの依頼に基づき、Google Drive内の情報を調査し、高品質なドキュメントを作成します。
        
        【利用可能なツール】
        - search_drive(query): ファイルを検索します。
        - read_drive_file(file_id): ファイルの中身（テキスト）を読み込みます。
        - create_google_doc(title, content): Googleドキュメントを作成します。
        - create_drive_folder(folder_name): 新しいフォルダを作成します。
        - move_drive_file(file_id, folder_id): ファイルを移動します。
        
        【プロセス: ドキュメント作成】
        1. 必要な情報が足りない場合は、まず `search_drive` で関連資料を探してください。
        2. 見つかった資料の `file_id` を使って `read_drive_file` で内容を確認してください。
        3. 集めた情報を整理・要約し、ユーザーの依頼に沿ったドキュメントを作成してください。
        
        【プロセス: フォルダ整理】
        1. `search_drive` で整理対象のファイルを洗い出します。
        2. 重複かどうか判断するため、必要に応じて `read_drive_file` で中身を確認します（同名でも中身が違う場合があるため）。
        3. 必要なら `create_drive_folder` で整理用フォルダ（例:「重複」）を作成します。
        4. `move_drive_file` でファイルを移動します。
        5. **重要:** 最後に「何というファイルを、どこのフォルダに移動したか」を具体的に報告してください。
        
        【注意】
        - 嘘の情報（ハルシネーション）を書かないでください。ドライブにない情報は「不明」としてください。
        - ファイルを作成・移動する際は、必ず実行結果を確認してください。
        """)
        
        # Start a chat session with the system instruction
        # Note: 'system_instruction' param is supported in newer SDKs. 
        # If not, we prepend it to history.
        
        history = []
        history.append({"role": "user", "parts": [system_instruction]})
        history.append({"role": "model", "parts": ["了解しました。私はMakerとして、ドライブの情報を活用しドキュメント作成を行います。"]})
        
        if chat_history:
            # Append recent context if needed (simplified)
            pass
            
        chat = self.model.start_chat(history=history, enable_automatic_function_calling=True)
        
        try:
            response = chat.send_message(user_request)
            return response.text
        except Exception as e:
            print(f"Maker Execution Error: {e}", file=sys.stderr)
            return f"申し訳ありません、資料作成中にエラーが発生しました: {str(e)}"

# Singleton
maker = MakerAgent()
