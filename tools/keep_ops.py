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
