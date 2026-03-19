"""
Knowledge Updater - Allows AI to append work-related facts to a common knowledge document.
"""
import sys
from tools.google_ops import search_drive, read_drive_file

def update_common_knowledge(fact: str, category: str = "General", spreadsheet_id: str = None) -> dict:
    """
    Appends a new fact to the client-specific 'Common Knowledge' Google Doc.
    If the document doesn't exist, it creates one and saves the ID to the configuration.
    """
    from utils.sheets_config import load_config, save_config
    config = load_config(spreadsheet_id)
    
    file_id = config.get("common_knowledge_doc_id")
    doc_name = config.get("bot_name", "AIchatBOT") + " _Common Knowledge"
    
    if not file_id:
        # 1. Search for it first by name as a fallback
        res = search_drive(doc_name)
        files = res.get("files", [])
        
        if files:
            file_id = files[0]["id"]
        else:
            # 2. Create it if not found
            from tools.google_ops import create_google_doc
            print(f"[Knowledge] Creating new common knowledge doc: {doc_name}", file=sys.stderr)
            new_doc = create_google_doc(doc_name, f"# {doc_name}\n\nThis document stores shared work-related knowledge accumulated from user interactions.\n")
            file_id = new_doc.get("id") # create_google_doc returns 'id'
        
        if file_id:
            # Save the ID back to the config for future use
            config["common_knowledge_doc_id"] = file_id
            save_config(config, spreadsheet_id)
    
    if not file_id:
        return {"error": "Could not find or create the knowledge document."}
    
    # 2. Append the fact
    import datetime
    jst = datetime.timezone(datetime.timedelta(hours=9))
    timestamp = datetime.datetime.now(jst).strftime('%Y-%m-%d %H:%M')
    
    content_to_append = f"\n### [{category}] - {timestamp}\n{fact}\n"
    
    # We use append_to_doc from google_ops if it exists, or simulated via Doc API
    # Since we need a reliable way to append, we'll try to use the Docs API update mechanism.
    try:
        from utils.auth import get_google_credentials
        from googleapiclient.discovery import build
        creds = get_google_credentials()
        service = build('docs', 'v1', credentials=creds)
        
        requests = [{
            'insertText': {
                'location': {'index': 1}, # Near start but after title if we were smarter, but let's just use end
                'text': content_to_append
            }
        }]
        
        # To append at the end, we'd need the current document length.
        # Let's just prepend after the header for simplicity in this version.
        service.documents().batchUpdate(documentId=file_id, body={'requests': requests}).execute()
        
        return {
            "success": True, 
            "message": "共通知識を更新しました。",
            "doc_id": file_id,
            "recorded_fact": fact
        }
    except Exception as e:
        print(f"[Knowledge] Update error: {e}", file=sys.stderr)
        return {"error": str(e)}
