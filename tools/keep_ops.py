"""
Google Keep Operations
Using the official Google Keep API (Enterprise/Workspace).
"""
import sys
from googleapiclient.discovery import build
from utils.auth import get_google_credentials

def get_keep_service():
    """Build and return the Keep service."""
    creds = get_google_credentials()
    if not creds:
        return None
    return build('keep', 'v1', credentials=creds)

def create_note(title, content):
    """
    Create a new note in Google Keep.
    
    Args:
        title: Note title
        content: Note body text
        
    Returns:
        Dict with success status and note details
    """
    try:
        service = get_keep_service()
        if not service:
            return {"error": "Google認証に失敗しました。"}
            
        note_body = {
            'title': title,
            'body': {
                'text': {
                    'text': content
                }
            }
        }
        
        # Create the note
        note = service.notes().create(body=note_body).execute()
        
        # Construct a direct link if possible (Keep API doesn't return webViewLink directly, 
        # but we can construct it or just return the ID)
        # Note name is like 'notes/ID'
        note_id = note.get('name', '').split('/')[-1]
        url = f"https://keep.google.com/u/0/#NOTE/{note_id}"
        
        return {
            "success": True,
            "message": f"Google Keepにメモ「{title}」を作成しました。",
            "note_id": note.get('name'),
            "url": url
        }
        
    except Exception as e:
        print(f"Keep create error: {e}", file=sys.stderr)
        return {"error": f"Keepメモ作成エラー: {str(e)}"}

def search_notes(query):
    """
    Search/List notes in Google Keep.
    Note: Keep API doesn't have a strong 'search' parameter in list(),
    so we list and filter client-side or just list recent ones.
    
    Args:
        query: Text to search for (client-side filtering)
    """
    try:
        service = get_keep_service()
        if not service:
            return {"error": "Google認証に失敗しました。"}
            
        # List notes (default returns active notes)
        results = service.notes().list().execute()
        notes = results.get('notes', [])
        
        # Filter client-side since API filter is limited
        matched_notes = []
        for note in notes:
            title = note.get('title', '')
            body_text = note.get('body', {}).get('text', {}).get('text', '')
            
            if query.lower() in title.lower() or query.lower() in body_text.lower():
                note_id = note.get('name', '').split('/')[-1]
                matched_notes.append({
                    'title': title,
                    'snippet': body_text[:100] + "..." if len(body_text) > 100 else body_text,
                    'url': f"https://keep.google.com/u/0/#NOTE/{note_id}"
                })
        
        return {
            "success": True,
            "count": len(matched_notes),
            "notes": matched_notes
        }
        
    except Exception as e:
        if "403" in str(e):
             return {"error": "Google Keep APIが有効になっていないか、権限がありません。GCPコンソールでKeep APIを有効化してください。"}
        return {"error": f"Keep検索エラー: {str(e)}"}


def update_keep_note(note_id: str, new_content: str) -> dict:
    """
    Update the content of an existing Google Keep note.
    
    Args:
        note_id: The resource name (ID) of the note to update (e.g., 'notes/xxx')
                 If just 'xxx' is provided, 'notes/' is prepended automatically.
        new_content: The new text content for the note.
    """
    try:
        service = get_keep_service()
        if not service:
            return {"error": "Google認証に失敗しました。"}
            
        # Ensure correct formatting of note resource name
        if not note_id.startswith('notes/'):
            note_id = f"notes/{note_id}"
            
        # Get existing note to preserve title
        # Keep API doesn't support partial updates easily, so we usually recreate body
        existing_note = service.notes().get(name=note_id).execute()
        
        # Keep API v1 does not have an 'update' method.
        # We must create a new note and delete the old one.
        title = existing_note.get('title', '')
        
        # 1. Create new note with same title but new content
        note_body = {
            'title': title,
            'body': {
                'text': {
                    'text': new_content
                }
            }
        }
        updated_note = service.notes().create(body=note_body).execute()
        
        # 2. Delete the old note
        try:
            service.notes().delete(name=note_id).execute()
        except Exception as delete_err:
            print(f"Warning: Could not delete old note {note_id}: {delete_err}", file=sys.stderr)
        
        url_id = updated_note.get('name', '').split('/')[-1]
        url = f"https://keep.google.com/u/0/#NOTE/{url_id}"
        
        return {
            "success": True,
            "message": f"Keepメモを更新しました。",
            "note_id": updated_note.get('name'),
            "url": url
        }
        
    except Exception as e:
        print(f"Keep update error: {e}", file=sys.stderr)
        return {"error": f"Keepメモ更新エラー: {str(e)}"}
