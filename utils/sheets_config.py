"""
Google Sheets-based configuration storage for KOTO
This replaces local file storage to enable cloud persistence.
"""
import json
import sys
from googleapiclient.discovery import build
from utils.auth import get_google_credentials, get_shared_folder_id

CONFIG_SHEET_NAME = "KOTO_CONFIG"

DEFAULT_CONFIG = {
    "user_name": "井崎さん",
    "personality": "元気な秘書",
    "knowledge_sources": [],
    "reminders": [
        {
            "name": "朝のリマインダー",
            "time": "07:00",
            "prompt": "今日の天気、今日・明日・今週の予定とタスクを確認して、まとめて教えて！最後に今日も頑張ろうという気持ちになる一言をお願い！",
            "enabled": True
        }
    ],
    "master_prompt": "",
    "notion_databases": []  # List of {id, name, description}
}

_config_sheet_id = None  # Cache

def get_or_create_config_sheet():
    """Get or create the KOTO_CONFIG spreadsheet in the shared folder"""
    global _config_sheet_id
    if _config_sheet_id:
        return _config_sheet_id
    
    try:
        creds = get_google_credentials()
        if not creds:
            print("Auth failed in sheets_config", file=sys.stderr)
            return None
            
        drive_service = build('drive', 'v3', credentials=creds)
        sheets_service = build('sheets', 'v4', credentials=creds)
        
        folder_id = get_shared_folder_id()
        
        # Search for existing config sheet
        query = f"name = '{CONFIG_SHEET_NAME}' and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false"
        if folder_id:
            query += f" and '{folder_id}' in parents"
            
        results = drive_service.files().list(
            q=query,
            pageSize=1,
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        
        files = results.get('files', [])
        
        if files:
            _config_sheet_id = files[0]['id']
            print(f"Found existing config sheet: {_config_sheet_id}", file=sys.stderr)
            return _config_sheet_id
        
        # Create new spreadsheet
        file_metadata = {
            'name': CONFIG_SHEET_NAME,
            'mimeType': 'application/vnd.google-apps.spreadsheet'
        }
        if folder_id:
            file_metadata['parents'] = [folder_id]
            
        file = drive_service.files().create(
            body=file_metadata,
            fields='id',
            supportsAllDrives=True
        ).execute()
        
        _config_sheet_id = file.get('id')
        print(f"Created new config sheet: {_config_sheet_id}", file=sys.stderr)
        
        # Initialize with default config
        save_config(DEFAULT_CONFIG)
        
        return _config_sheet_id
        
    except Exception as e:
        print(f"Error in get_or_create_config_sheet: {e}", file=sys.stderr)
        return None

def load_config():
    """Load configuration from Google Sheets"""
    try:
        sheet_id = get_or_create_config_sheet()
        if not sheet_id:
            return DEFAULT_CONFIG
            
        creds = get_google_credentials()
        if not creds:
            return DEFAULT_CONFIG
            
        sheets_service = build('sheets', 'v4', credentials=creds)
        
        # Read from A1 (JSON string stored there)
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range='A1'
        ).execute()
        
        values = result.get('values', [])
        if values and values[0]:
            config_json = values[0][0]
            config = json.loads(config_json)
            # Merge with defaults to handle missing keys
            merged = {**DEFAULT_CONFIG, **config}
            print(f"Config loaded from sheet {_config_sheet_id}", file=sys.stderr)
            return merged
        else:
            return DEFAULT_CONFIG
            
    except Exception as e:
        print(f"Error loading config from sheets: {e}", file=sys.stderr)
        return DEFAULT_CONFIG

def save_config(config):
    """Save configuration to Google Sheets"""
    try:
        sheet_id = get_or_create_config_sheet()
        if not sheet_id:
            return False
            
        creds = get_google_credentials()
        if not creds:
            return False
            
        sheets_service = build('sheets', 'v4', credentials=creds)
        
        # Store as JSON string in A1
        config_json = json.dumps(config, ensure_ascii=False, indent=2)
        
        sheets_service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range='A1',
            valueInputOption='RAW',
            body={'values': [[config_json]]}
        ).execute()
        
        print(f"Config saved to sheet {sheet_id}", file=sys.stderr)
        return True
        
    except Exception as e:
        print(f"Error saving config to sheets: {e}", file=sys.stderr)
        return False
