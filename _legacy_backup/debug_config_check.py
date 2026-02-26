import os
import sys
import json
from googleapiclient.discovery import build
from google.oauth2 import service_account

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.auth import get_google_credentials, get_shared_folder_id

def check_clean():
    creds = get_google_credentials()
    drive = build('drive', 'v3', credentials=creds)
    sheets = build('sheets', 'v4', credentials=creds)
    folder_id = get_shared_folder_id()
    
    # Check Target Folder
    if folder_id:
        q = f"name = 'KOTO_CONFIG' and '{folder_id}' in parents and trashed = false"
        res = drive.files().list(
            q=q, 
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        files = res.get('files', [])
        
        for f in files:
            print(f"ID: {f['id']}")
            try:
                res = sheets.spreadsheets().values().get(spreadsheetId=f['id'], range='A1').execute()
                val = res.get('values', [['{}']])[0][0]
                data = json.loads(val)
                for r in data.get('reminders', []):
                    print(f"  - {r.get('time')} ({r.get('name')}) Enabled:{r.get('enabled')}")
            except Exception as e:
                print(f"  Error: {e}")

if __name__ == "__main__":
    check_clean()
