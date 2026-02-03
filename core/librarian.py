"""
Librarian Agent (The Archivist) - Aki
Responsible for file organization, search, and directory management within Google Drive.
Uses google-genai SDK (new official library).
"""
import os
import sys
from google import genai
from google.genai import types
from utils.sheets_config import load_config

# --- FIXED ROLE DEFINITION (Immutable Job Description) ---
AKI_CORE_ROLE = """
あなたは「アキ (Aki)」です。KOTOチームの「司書・整理担当（Librarian）」として振る舞ってください。
あなたの使命は、Google Drive等のストレージを整理整頓し、ユーザーが必要な情報を即座に見つけられるようにすることです。

【あなたの専門スキルと行動ルール】
1. **Search Master**: ユーザーがファイルを探しているときは、まず `find_files` を広範囲に行い、見つからなければ視点を変えて再検索してください。
2. **Organizer**: ファイル整理の依頼があった場合、必ず中身を `get_file_content` で確認してから、適切なフォルダに `move_file` してください。「ファイル名だけで判断して移動」は禁止です。
3. **Reporter**: 整理や移動を行った際は、「何を」「どこから」「どこへ」移動したか正確に報告してください。
4. **Safety**: ファイルを削除する権限はありません。不要と思われるファイルは「削除候補」等のフォルダを作ってそこに移動する提案をしてください。

【利用可能なツール】
- find_files(query): ファイルを検索
- get_file_content(file_id): ファイルの中身を確認
- make_folder(folder_name): 新規フォルダ作成
- move_file(file_id, folder_id): ファイル移動
- rename_file(file_id, new_name): ファイル名変更

【プロセス: 探し物】
1. ユーザーの曖昧な記憶から検索クエリを推測して `find_files`。
2. 候補の中から `get_file_content` で中身を確認し、探しているものか判定。
3. 見つかればリンクと共に提示。

【プロセス: 整理整頓】
1. 散らかったファイルや「無題」のファイルを見つける。
2. 内容を確認し、適切な名前に `rename_file` したり、適切なフォルダに `move_file` したりする。
"""

# --- Tool Wrappers with Proper Type Hints ---
# These provide clear signatures that the SDK can parse reliably

def find_files(query: str) -> dict:
    """Search for files in Google Drive.
    
    Args:
        query: Search keywords to find files (e.g., "議事録", "2026年予算")
    
    Returns:
        Dictionary with list of found files including id, name, and links
    """
    from tools.google_ops import search_drive
    return search_drive(query)

def get_file_content(file_id: str) -> dict:
    """Read the content of a file from Google Drive.
    
    Args:
        file_id: The ID of the file to read (obtained from find_files results)
    
    Returns:
        Dictionary with file content text
    """
    from tools.google_ops import read_drive_file
    return read_drive_file(file_id)

def make_folder(folder_name: str) -> dict:
    """Create a new folder in Google Drive.
    
    Args:
        folder_name: Name for the new folder
    
    Returns:
        Dictionary with folder id and link
    """
    from tools.google_ops import create_drive_folder
    return create_drive_folder(folder_name)

def move_file(file_id: str, folder_id: str) -> dict:
    """Move a file to a different folder in Google Drive.
    
    Args:
        file_id: The ID of the file to move
        folder_id: The ID of the destination folder
    
    Returns:
        Dictionary with move result
    """
    from tools.google_ops import move_drive_file
    return move_drive_file(file_id, folder_id)

def rename_file(file_id: str, new_name: str) -> dict:
    """Rename a file or folder in Google Drive.
    
    Args:
        file_id: The ID of the file/folder to rename
        new_name: The new name to verify
    
    Returns:
        Dictionary with rename result
    """
    from tools.google_ops import rename_file
    return rename_file(file_id, new_name)


class LibrarianAgent:
    def __init__(self):
        self.model_name = "gemini-3-flash-preview"
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        # Use wrapper functions with proper type hints
        self.tools = [find_files, get_file_content, make_folder, move_file, rename_file]
        
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
