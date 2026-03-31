"""
Conversation history storage - JSON file based persistence
"""
import json
import os
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Storage file path
DATA_DIR = Path(__file__).parent.parent / "data"
HISTORY_FILE = DATA_DIR / "history.json"

# In-memory cache
_history_cache = None

# Maximum history per user (keep short to avoid old tool call patterns confusing AI)
MAX_HISTORY = 10


def _ensure_data_dir():
    """Ensure data directory exists"""
    DATA_DIR.mkdir(exist_ok=True)


def load_all_history():
    """Load all conversation history from file"""
    global _history_cache
    
    if _history_cache is not None:
        return _history_cache
    
    _ensure_data_dir()
    
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
                
                # Sanitize history (Auto-heal corrupted data)
                sanitized = False
                for user_id, messages in loaded_data.items():
                    for msg in messages:
                        if msg.get("text") is None:
                            msg["text"] = "(Restored empty message)"
                            sanitized = True
                
                if sanitized:
                    print("Fixed corrupted history entries.", file=sys.stderr)
                    # We don't save immediately here to avoid write loops, 
                    # but it will be saved on next message add.
                
                _history_cache = defaultdict(list, loaded_data)
        except Exception as e:
            print(f"Error loading history: {e}")
            _history_cache = defaultdict(list)
    else:
        # Try restoration from Drive if local file missing (e.g. after restart)
        restored = _restore_from_drive()
        if restored:
            _history_cache = defaultdict(list, restored)
            print("History restored from Drive!", file=sys.stderr)
        else:
            _history_cache = defaultdict(list)
    
    return _history_cache


def save_all_history():
    """Save all conversation history to file"""
    global _history_cache
    
    if _history_cache is None:
        return
    
    _ensure_data_dir()
    
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(dict(_history_cache), f, ensure_ascii=False, indent=2)
    except OSError as e:
        # Vercel is read-only. Log warning but don't crash or spam errors.
        pass
    except Exception as e:
        print(f"Error saving history: {e}", file=sys.stderr)
    
    # Run backup in background
    import threading
    threading.Thread(target=backup_history_to_drive).start()


def backup_history_to_drive():
    """Sync history to Google Drive (mora_history_backup.json)"""
    global _history_cache
    if _history_cache is None: 
        return

    try:
        from tools.google_ops import upload_file_to_drive, search_drive
        import io
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseUpload
        from utils.auth import get_google_credentials

        print("Starting Drive backup...", file=sys.stderr)
        
        # JSON dump to string
        json_str = json.dumps(dict(_history_cache), ensure_ascii=False, indent=2)
        
        # Check for existing
        res = search_drive("mora_history_backup.json")
        files = res.get("files", [])
        file_id = None
        if files:
            file_id = files[0]['id']
        
        if file_id:
            # Update existing
            creds = get_google_credentials()
            if not creds:
                print("Backup Error: No creds", file=sys.stderr)
                return
                
            service = build('drive', 'v3', credentials=creds)
            # Encode correctly
            media = MediaIoBaseUpload(io.BytesIO(json_str.encode('utf-8')), mimetype='application/json', resumable=True)
            service.files().update(
                fileId=file_id, 
                media_body=media,
                supportsAllDrives=True
            ).execute()
            print(f"Backup updated: {file_id}", file=sys.stderr)
        else:
            # Create new
            res = upload_file_to_drive("mora_history_backup.json", json_str.encode('utf-8'), mime_type='application/json')
            print(f"Backup created: {res}", file=sys.stderr)
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Drive backup error: {e}", file=sys.stderr)

def _restore_from_drive():
    """Try to restore history from Drive"""
    print("Attempting to restore history from Drive...", file=sys.stderr)
    try:
        from tools.google_ops import search_drive, read_drive_file
        res = search_drive("mora_history_backup.json")
        files = res.get("files", [])
        if files:
            file_id = files[0]['id']
            # read_drive_file returns content string
            res_read = read_drive_file(file_id)
            if res_read.get("success"):
                content = res_read.get("content", "")
                if content:
                    return json.loads(content)
    except Exception as e:
        print(f"Drive restore error: {e}", file=sys.stderr)
    return None


def get_user_history(user_id):
    """Get conversation history for a specific user"""
    history = load_all_history()
    return history[user_id]


def add_message(user_id, role, text):
    """Add a message to user's conversation history"""
    history = load_all_history()
    
    history[user_id].append({
        "role": role,
        "text": text,
        "timestamp": datetime.now().isoformat()
    })
    
    # Trim to max history
    if len(history[user_id]) > MAX_HISTORY:
        history[user_id] = history[user_id][-MAX_HISTORY:]
    
    # Save after each message
    save_all_history()


def clear_user_history(user_id):
    """Clear conversation history for a specific user"""
    history = load_all_history()
    history[user_id] = []
    save_all_history()


def get_max_history():
    """Get the maximum history limit"""
    return MAX_HISTORY
