
import sys
import os
import json
from googleapiclient.discovery import build

# Setup paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, ROOT_DIR)

from utils.auth import get_google_credentials
from tools.google_ops import search_drive

def init_sheet():
    creds = get_google_credentials()
    if not creds:
        print("Auth failed")
        return
    
    # 1. Find Spreadsheet ID by name
    sheet_name = 'AIchatBOT_Master_Registry'
    res = search_drive(sheet_name)
    files = res.get('files', [])
    if not files:
        print(f"Spreadsheet '{sheet_name}' not found.")
        return
    
    spreadsheet_id = files[0]['id']
    print(f"Found Spreadsheet ID: {spreadsheet_id}")
    
    service = build('sheets', 'v4', credentials=creds)
    
    # 2. Define Headers
    headers = [
        "client_id", 
        "bot_name", 
        "personality", 
        "line_channel_secret", 
        "line_channel_access_token", 
        "knowledge_folder_id", 
        "spreadsheet_id"
    ]
    
    # 3. Load current master_config.json to populate initial data
    # (Try to find it in root)
    config_path = os.path.join(ROOT_DIR, 'master_config.json')
    if not os.path.exists(config_path):
        print(f"master_config.json not found at {config_path}")
        return
        
    with open(config_path, 'r', encoding='utf-8') as f:
        master = json.load(f)
    
    rows = [headers]
    for cid, config in master.items():
        rows.append([
            cid,
            config.get('bot_name', ''),
            config.get('personality', ''),
            config.get('line_channel_secret', ''),
            config.get('line_channel_access_token', ''),
            config.get('knowledge_folder_id', ''),
            config.get('spreadsheet_id', '')
        ])
    
    # 4. Update Sheet
    body = {
        'values': rows
    }
    
    try:
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range='A1',
            valueInputOption='RAW',
            body=body
        ).execute()
        print(f"Master Registry initialized with {len(rows)-1} clients.")
        print(f"Registry Sheet ID is: {spreadsheet_id}")
    except Exception as e:
        print(f"Failed to update sheet: {e}")

if __name__ == "__main__":
    init_sheet()
