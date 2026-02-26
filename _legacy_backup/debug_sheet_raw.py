from utils.sheets_config import get_or_create_config_sheet
from utils.auth import get_google_credentials
from googleapiclient.discovery import build
import sys
import json

print("Dumping Raw Sheet Content...")
try:
    sheet_id = get_or_create_config_sheet()
    if not sheet_id:
        print("No sheet ID found.")
        sys.exit(1)
        
    creds = get_google_credentials()
    service = build('sheets', 'v4', credentials=creds)
    
    # Read all data
    result = service.spreadsheets().values().get(
        spreadsheetId=sheet_id, range="A:B"
    ).execute()
    rows = result.get('values', [])
    
    print(f"Sheet ID: {sheet_id}")
    print(f"Row Count: {len(rows)}")
    print("--- RAW DATA ---")
    for row in rows:
        print(row)
        
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Dump error: {e}")
