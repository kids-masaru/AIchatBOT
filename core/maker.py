"""
Maker Agent (The Writer)
Specialized in creating documents (Docs, Slides, Spreadsheets) by researching Google Drive.
Uses google-genai SDK (new official library).
"""
import os
import sys
from google import genai
from google.genai import types
from tools.google_ops import search_drive, read_drive_file, create_google_doc, create_google_sheet, create_google_slide, move_drive_file, create_drive_folder
from utils.sheets_config import load_config

# --- FIXED ROLE DEFINITION (Immutable Job Description) ---
FUMI_CORE_ROLE = """
あなたは「フミ (Fumi)」です。KOTOチームの「資料作成担当（Creator）」として振る舞ってください。
あなたの使命は、ユーザーの依頼に基づき、高品質なドキュメント、スプレッドシート、プレゼンテーションを作成することです。

【あなたの専門スキルと行動ルール】
1. **Drive Research**: 作成前に必ず `search_drive` と `read_drive_file` を使い、関連情報を調査してください。想像で書かず、事実に基づいた資料を作ることがあなたのポリシーです。
2. **Quality Output**: ドキュメント作成時は、単なるテキストの羅列ではなく、見出しや箇条書きを使った読みやすい構成を心がけてください。
3. **Execution**: 提案だけでなく、実際にツールを使ってファイルを作成 (`create_...`) してください。
4. **Safety**: 既存のファイルを上書きしたり削除したりするツールは持っていません。常に新規作成を行います。

【利用可能なツール】
- search_drive(query): Google Drive内のファイルを検索
- read_drive_file(file_id): ファイルのテキスト内容を読み込み
- create_google_doc(title, content): Googleドキュメントを新規作成
- create_google_sheet(title): Googleスプレッドシートを新規作成
- create_google_slide(title): Googleスライドを新規作成
- create_drive_folder(folder_name): 整理用のフォルダを作成
- move_drive_file(file_id, folder_id): ファイルを特定のフォルダへ移動

【プロセス: ドキュメント作成の標準フロー】
1. **調査**: ユーザーの依頼に関連するキーワードで `search_drive` を実行。
2. **読解**: ヒットしたファイルの中身を `read_drive_file` で確認（複数可）。
3. **構成**: 集めた情報を整理し、ドキュメントの構成を練る。
4. **作成**: `create_google_doc` 等を実行して実ファイルを作成。
5. **報告**: 作成したファイルのURLと、どのような意図で作ったかをユーザーに報告。

【プロセス: フォルダ整理の標準フロー】
1. `search_drive` で対象ファイルをリストアップ。
2. `read_drive_file` で内容を確認（重複チェックなど）。
3. `create_drive_folder` で適切なフォルダを作成。
4. `move_drive_file` で移動。
5. 移動結果（数と移動先）を報告。
"""

class MakerAgent:
    def __init__(self):
        self.model_name = "gemini-3-flash-preview"
        # New SDK uses GEMINI_API_KEY env var automatically
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        # Tools are passed as Python functions directly
        self.tools = [
            search_drive, 
            read_drive_file, 
            create_google_doc, 
            create_google_sheet, 
            create_google_slide, 
            move_drive_file, 
            create_drive_folder
        ]
        
    def run(self, user_request: str, chat_history: list = None) -> str:
        """
        Execute the maker task using the new google-genai SDK with automatic function calling.
        """
        print(f"Maker(Fumi): Starting with request: {user_request}", file=sys.stderr)
        
        # 1. Load User Configuration (Personality/Add-on Instructions)
        config_data = load_config()
        user_instruction = config_data.get('fumi_instruction', '')
        
        # 2. Construct the Composite System Prompt
        system_instruction = f"{FUMI_CORE_ROLE}\n\n"
        
        if user_instruction:
            system_instruction += f"【ユーザーからの追加指示（性格・振る舞い・特記事項）】\n{user_instruction}\n"
            system_instruction += "※上記の指示がCore Roleと矛盾する場合は、Core Role（資料作成の遂行）を優先しつつ、可能な限りトーンや方針を取り入れてください。"
        
        # 3. Build content with system instruction prepended
        full_prompt = f"{system_instruction}\n\n【ユーザーからの依頼】\n{user_request}"
        
        try:
            # 4. Configure and call using new SDK
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
            print(f"Maker(Fumi) Execution Error: {e}", file=sys.stderr)
            return f"申し訳ありません、Fumiの処理中にエラーが発生しました: {str(e)}"

# Singleton
maker = MakerAgent()
