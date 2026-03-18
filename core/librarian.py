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
# --- Librarian Agent (Aki) ---
# Instructions are now fully managed in the Spreadsheet configuration.

# --- Tool Wrappers with Proper Type Hints ---
# These provide clear signatures that the SDK can parse reliably

def find_files(query: str, folder_id: str = None) -> dict:
    """Search for files in Google Drive.
    
    Args:
        query: Search keywords to find files (e.g., "議事録", "2026年予算")
        folder_id: (Optional) Set this to a specific folder ID to restrict the search to that folder.
    
    Returns:
        Dictionary with list of found files including id, name, and links
    """
    from tools.google_ops import search_drive
    return search_drive(query, folder_id=folder_id)

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

def list_drive_folders(parent_id: str = None) -> dict:
    """List folders in Google Drive for step-by-step searching.
    If parent_id is None, lists root folders and Shared Drives.
    """
    from tools.google_ops import list_drive_folders
    return list_drive_folders(parent_id)

def copy_drive_file(file_id: str, new_name: str, folder_id: str = None) -> dict:
    """Make a copy of a file in Google Drive.
    
    Args:
        file_id: ID of the file to copy
        new_name: Name for the copied file
        folder_id: (Optional) ID of the folder to put the copy in
    """
    from tools.google_ops import copy_drive_file
    return copy_drive_file(file_id, new_name, folder_id)


class LibrarianAgent:
    def __init__(self):
        self.model_name = "gemini-3-flash-preview"
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        # Use wrapper functions with proper type hints
        self.tools = [find_files, get_file_content, make_folder, move_file, rename_file, list_drive_folders, copy_drive_file]
        
    def run(self, user_request: str, chat_history: list = None) -> str:
        """
        Execute the librarian task using google-genai SDK.
        """
        print(f"Librarian(Aki): Starting with request: {user_request}", file=sys.stderr)
        
        # 1. Load User Configuration
        config_data = load_config()
        user_instruction = config_data.get('aki_instruction', '')
        knowledge_sources = config_data.get('knowledge_sources', [])
        
        # 2. Construct System Prompt
        import datetime
        jst = datetime.timezone(datetime.timedelta(hours=9))
        now_str = datetime.datetime.now(jst).strftime('%Y-%m-%d %H:%M:%S (%A)')
        
        system_instruction = f"現在のシステム日時: {now_str}\n\n"
        system_instruction += "【あなたの指示・役割】\n"
        system_instruction += user_instruction if user_instruction else "あなたは整理担当のアキです。"
        
        if knowledge_sources:
            system_instruction += "\n\n【登録済みの重要フォルダ指定（Dashboard Knowledge Sources）】\n"
            system_instruction += "以下のフォルダにはユーザーから特別な指示が割り当てられています。\n"
            system_instruction += "検索や移動を行う際、対象が以下の指示に該当する場合は、全体検索ではなく必ずこのfolder_idを指定して `find_files(query, folder_id)` を実行してください。\n"
            for source in knowledge_sources:
                f_name = source.get('name', 'Unknown')
                f_id = source.get('id', '')
                f_inst = source.get('instruction', '')
                system_instruction += f"- フォルダ名: {f_name} (ID: {f_id})\n  指示: {f_inst}\n\n"
        
        system_instruction += "\n※指示内容（整理・検索の遂行）を最優先してください。"
            
        try:
            # Prepare contents
            contents = [types.Content(role="user", parts=[types.Part.from_text(text=user_request)])]
            
            gen_config = types.GenerateContentConfig(
                tools=self.tools,
                system_instruction=system_instruction,
                temperature=0.2, # Lower temperature for stable tool use
            )
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=gen_config,
            )

            return response.text if response.text else "申し訳ありません、ファイルを操作できませんでした。"

        except Exception as e:
            print(f"Librarian(Aki) Execution Error: {e}", file=sys.stderr)
            return f"アキです。すみません、処理中にエラーが起きてしまいました...: {str(e)}"

# Singleton
librarian = LibrarianAgent()
