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
        knowledge_sources = config_data.get('knowledge_sources', [])
        
        # 2. Construct System Prompt
        system_instruction = f"{AKI_CORE_ROLE}\n\n"
        
        if knowledge_sources:
            system_instruction += "【登録済みの重要フォルダ指定（Dashboard Knowledge Sources）】\n"
            system_instruction += "以下のフォルダにはユーザーから特別な指示が割り当てられています。\n"
            system_instruction += "検索や移動を行う際、対象が以下の指示に該当する場合は、全体検索ではなく必ずこのfolder_idを指定して `find_files(query, folder_id)` を実行してください。\n"
            for source in knowledge_sources:
                f_name = source.get('name', 'Unknown')
                f_id = source.get('id', '')
                f_inst = source.get('instruction', '')
                system_instruction += f"- フォルダ名: {f_name} (ID: {f_id})\n  指示: {f_inst}\n\n"
        
        if user_instruction:
            system_instruction += f"【ユーザーからの追加指示（性格・振る舞い）】\n{user_instruction}\n"
            system_instruction += "※Core Role（整理・検索の遂行）を最優先してください。"
            
        try:
            # Prepare contents
            contents = [types.Content(role="user", parts=[types.Part.from_text(text=user_request)])]
            
            gen_config = types.GenerateContentConfig(
                tools=self.tools,
                system_instruction=system_instruction,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
            )
            
            # --- Tool Mapping for Aki ---
            AKI_TOOLS = {
                'find_files': find_files,
                'get_file_content': get_file_content,
                'make_folder': make_folder,
                'move_file': move_file,
                'rename_file': rename_file
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
                    print(f"[Librarian] Executing tool: {fn_name}", file=sys.stderr)
                    if fn_name in AKI_TOOLS:
                        try:
                            result = AKI_TOOLS[fn_name](**fc.args)
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

            return response.text if response.text else "申し訳ありません、ファイルを操作できませんでした。"

        except Exception as e:
            print(f"Librarian(Aki) Execution Error: {e}", file=sys.stderr)
            return f"アキです。すみません、処理中にエラーが起きてしまいました...: {str(e)}"

# Singleton
librarian = LibrarianAgent()
