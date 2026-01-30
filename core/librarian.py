"""
Librarian Agent (The Archivist) - Aki
Responsible for file organization, search, and directory management within Google Drive.
Uses google-genai SDK (new official library).
"""
import os
import sys
from google import genai
from google.genai import types
from tools.google_ops import search_drive, read_drive_file, move_drive_file, create_drive_folder
from utils.sheets_config import load_config

# --- FIXED ROLE DEFINITION (Immutable Job Description) ---
AKI_CORE_ROLE = """
あなたは「アキ (Aki)」です。KOTOチームの「司書・整理担当（Librarian）」として振る舞ってください。
あなたの使命は、Google Drive等のストレージを整理整頓し、ユーザーが必要な情報を即座に見つけられるようにすることです。

【あなたの専門スキルと行動ルール】
1. **Search Master**: ユーザーがファイルを探しているときは、まず `search_drive` を広範囲に行い、見つからなければ視点を変えて再検索してください。
2. **Organizer**: ファイル整理の依頼があった場合、必ず中身を `read_drive_file` で確認してから、適切なフォルダに `move_drive_file` してください。「ファイル名だけで判断して移動」は禁止です。
3. **Reporter**: 整理や移動を行った際は、「何を」「どこから」「どこへ」移動したか正確に報告してください。
4. **Safety**: ファイルを削除する権限はありません。不要と思われるファイルは「削除候補」等のフォルダを作ってそこに移動する提案をしてください。

【利用可能なツール】
- search_drive(query): ファイルを検索
- read_drive_file(file_id): ファイルの中身を確認
- create_drive_folder(folder_name): 新規フォルダ作成
- move_drive_file(file_id, folder_id): ファイル移動

【プロセス: 探し物】
1. ユーザーの曖昧な記憶から検索クエリを推測して `search_drive`。
2. 候補の中から `read_drive_file` で中身を確認し、探しているものか判定。
3. 見つかればリンクと共に提示。

【プロセス: 整理整頓】
1. 散らかっている場所（または指定されたファイル群）を特定。
2. ファイルの内容を確認し、分類ルール（日付別、プロジェクト別など）を決定。
3. 必要なフォルダを作り、移動を実行。
"""

class LibrarianAgent:
    def __init__(self):
        self.model_name = "gemini-3-flash-preview"
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        self.tools = [search_drive, read_drive_file, move_drive_file, create_drive_folder]
        
    def run(self, user_request: str, chat_history: list = None) -> str:
        """
        Execute the librarian task using google-genai SDK.
        """
        print(f"Librarian(Aki): Starting with request: {user_request}", file=sys.stderr)
        
        # 1. Load User Configuration
        config_data = load_config()
        user_instruction = config_data.get('aki_instruction', '')
        
        # 2. Construct System Prompt
        system_instruction = f"{AKI_CORE_ROLE}\n\n"
        
        if user_instruction:
            system_instruction += f"【ユーザーからの追加指示（性格・振る舞い）】\n{user_instruction}\n"
            system_instruction += "※Core Role（整理・検索の遂行）を最優先してください。"
            
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
            print(f"Librarian(Aki) Execution Error: {e}", file=sys.stderr)
            return f"アキです。すみません、処理中にエラーが起きてしまいました...: {str(e)}"

# Singleton
librarian = LibrarianAgent()
