"""
Maker Agent (The Writer) - Fumi
Specialized in creating documents (Docs, Slides, Spreadsheets) by researching Google Drive.
Uses google-genai SDK (new official library).
"""
import os
import sys
from google import genai
from google.genai import types
from utils.sheets_config import load_config

# --- Maker Agent (Fumi) ---
# Instructions are now fully managed in the Spreadsheet configuration.

# --- Tool Wrappers with Proper Type Hints ---
# These provide clear signatures that the SDK can parse reliably

def find_files(query: str) -> dict:
    """Search for files in Google Drive.
    
    Args:
        query: Search keywords to find files (e.g., "議事録", "テンプレート")
    
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

def create_document(title: str, content: str) -> dict:
    """Create a new Google Document.
    
    Args:
        title: Document title
        content: Text content to put in the document
    
    Returns:
        Dictionary with document URL
    """
    from tools.google_ops import create_google_doc
    return create_google_doc(title, content)

def create_spreadsheet(title: str, data: list[list[str | int | float]] = None) -> dict:
    """Create a new Google Spreadsheet.
    
    Args:
        title: Spreadsheet title
        data: Optional 2D list of values to write. Inner values can be strings or numbers. 
              Example: [["Name", "Age"], ["Alice", 30]]
    
    Returns:
        Dictionary with spreadsheet URL
    """
    from tools.google_ops import create_google_sheet
    return create_google_sheet(title, data)

def create_presentation(title: str, pages: list[dict] = None) -> dict:
    """Create a new Google Slides presentation.
    
    Args:
        title: Presentation title
        pages: Optional list of slides. Each slide is a dictionary with 'title' and 'body'.
               Example: [{"title": "Slide 1", "body": "Bullet points..."}]
    
    Returns:
        Dictionary with presentation URL
    """
    from tools.google_ops import create_google_slide
    return create_google_slide(title, pages)

def create_memo(title: str, content: str) -> dict:
    """Create a new note in Google Keep.
    
    Args:
        title: Note title
        content: Note content
    """
    from tools.keep_ops import create_note
    return create_note(title, content)

def search_memos(text: str) -> dict:
    """Search for notes in Google Keep.
    
    Args:
        text: Text to search for
    """
    from tools.keep_ops import search_notes
    return search_notes(text)

def update_keep_note(note_id: str, new_content: str) -> dict:
    """Update an existing Google Keep note.
    
    Args:
        note_id: The ID of the note to update (e.g., '1a2b3c...')
        new_content: The new text content for the note.
    """
    from tools.keep_ops import update_keep_note
    return update_keep_note(note_id, new_content)

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

def list_templates() -> dict:
    """List all available templates.
    
    Returns:
        Dictionary with list of templates
    """
    from tools.template_ops import list_templates as lt
    return lt()

def use_template_to_create(template_type: str, new_name: str) -> dict:
    """Create a new document from a template.
    
    Args:
        template_type: Type of template (e.g., "領収書", "議事録")
        new_name: Name for the new document
        
    Returns:
        Dictionary with new document URL
    """
    from tools.template_ops import find_template_by_type, copy_template
    
    result = find_template_by_type(template_type)
    if result.get("error"):
        return result
    if not result.get("found"):
        return {"error": f"「{template_type}」のテンプレートが見つかりません。"}
    
    template = result["template"]
    copy_result = copy_template(template["file_id"], new_name)
    
    if copy_result.get("error"):
        return copy_result
    
    return {
        "success": True,
        "message": f"テンプレート「{template['name']}」を使用して作成しました。",
        "url": copy_result.get("url"),
        "file_id": copy_result.get("file_id"), # file_id is crucial for replacement
        "fields": template.get("fields", [])
    }

def replace_doc_text(file_id: str, replacements: dict) -> dict:
    """Replace placeholders in a document.
    
    Args:
        file_id: Document ID
        replacements: Dictionary of placeholders to replace
    """
    from tools.template_ops import replace_placeholders
    return replace_placeholders(file_id, replacements)


class MakerAgent:
    def __init__(self):
        self.model_name = "gemini-3-flash-preview"
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        # Use wrapper functions with proper type hints
        self.tools = [
            find_files, 
            get_file_content, 
            create_document, 
            create_spreadsheet, 
            create_presentation, 
            make_folder,
            move_file,
            list_templates,
            use_template_to_create,
            replace_doc_text,
            create_memo,
            search_memos,
            update_keep_note
        ]
        
    def run(self, user_request: str, chat_history: list = None) -> str:
        """
        Execute the maker task using the new google-genai SDK with automatic function calling.
        """
        print(f"Maker(Fumi): Starting with request: {user_request}", file=sys.stderr)
        
        # 1. Load User Configuration (Personality/Add-on Instructions)
        config_data = load_config()
        user_instruction = config_data.get('fumi_instruction', '')
        
        # 2. Construct System Prompt
        import datetime
        jst = datetime.timezone(datetime.timedelta(hours=9))
        now_str = datetime.datetime.now(jst).strftime('%Y-%m-%d %H:%M:%S (%A)')
        
        system_instruction = f"現在のシステム日時: {now_str}\n\n"
        system_instruction += "【あなたの指示・役割】\n"
        system_instruction += user_instruction if user_instruction else "あなたは資料作成担当のフミです。"
        
        system_instruction += "\n\n※指示内容（特にKeepやDriveの操作権限）は最優先して遵守してください。"
            
        try:
            # Prepare contents
            contents = [types.Content(role="user", parts=[types.Part.from_text(text=user_request)])]
            
            gen_config = types.GenerateContentConfig(
                tools=self.tools,
                system_instruction=system_instruction,
                temperature=0.2
            )

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=gen_config,
            )

            return response.text if response.text else "申し訳ありません、資料を作成できませんでした。"

        except Exception as e:
            print(f"Maker(Fumi) Execution Error: {e}", file=sys.stderr)
            return f"申し訳ありません、Fumiの処理中にエラーが発生しました: {str(e)}"

# Singleton
maker = MakerAgent()
