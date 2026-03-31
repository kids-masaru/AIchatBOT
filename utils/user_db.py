"""
User Database using Google Sheets
Stores UserID, Location, and Notification Preferences
"""
import sys
import datetime
from googleapiclient.discovery import build
from utils.auth import get_google_credentials, get_shared_folder_id
from tools.google_ops import create_google_sheet, search_drive

DB_FILENAME = "Mora_Users"

def _get_or_create_db():
    """Find existing DB sheet or create new one"""
    try:
        # Search for existing file
        creds = get_google_credentials()
        drive_service = build('drive', 'v3', credentials=creds)
        
        results = drive_service.files().list(
            q=f"name = '{DB_FILENAME}' and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed=false",
            fields="files(id, name)",
            includeItemsFromAllDrives=True,
            supportsAllDrives=True
        ).execute()
        
        files = results.get('files', [])
        
        if files:
            return files[0]['id']
        
        # Create new if not found
        print(f"Creating new User DB: {DB_FILENAME}", file=sys.stderr)
        result = create_google_sheet(DB_FILENAME)
        if result.get('success'):
            # Initialize headers
            sheet_id = result['id']
            sheets_service = build('sheets', 'v4', credentials=creds)
            sheets_service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range='A1',
                valueInputOption='RAW',
                body={'values': [['User_ID', 'Location', 'Last_Updated', 'Status']]}
            ).execute()
            return sheet_id
        return None
        
    except Exception as e:
        print(f"DB Init Error: {e}", file=sys.stderr)
        return None

def register_user(user_id, location):
    """Update or Insert user location"""
    sheet_id = _get_or_create_db()
    if not sheet_id:
        return {"error": "データベースエラー"}
    
    try:
        creds = get_google_credentials()
        sheets_service = build('sheets', 'v4', credentials=creds)
        
        # Read all data
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=sheet_id, range='A:D'
        ).execute()
        rows = result.get('values', [])
        
        # Find user
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        updated = False
        
        for i, row in enumerate(rows):
            if i == 0: continue # Skip header
            if len(row) > 0 and row[0] == user_id:
                # Update existing row (Row numbers are 1-based)
                range_name = f'B{i+1}:D{i+1}'
                sheets_service.spreadsheets().values().update(
                    spreadsheetId=sheet_id,
                    range=range_name,
                    valueInputOption='RAW',
                    body={'values': [[location, now, 'ACTIVE']]}
                ).execute()
                updated = True
                break
        
        if not updated:
            # Append new row
            sheets_service.spreadsheets().values().append(
                spreadsheetId=sheet_id,
                range='A:D',
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body={'values': [[user_id, location, now, 'ACTIVE']]}
            ).execute()
            
        return {"success": True, "location": location}
        
    except Exception as e:
        print(f"Register Error: {e}", file=sys.stderr)
        return {"error": str(e)}

def get_active_users():
    """Get list of users with Status=ACTIVE"""
    sheet_id = _get_or_create_db()
    if not sheet_id:
        return []
        
    try:
        creds = get_google_credentials()
        sheets_service = build('sheets', 'v4', credentials=creds)
        
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=sheet_id, range='A:D'
        ).execute()
        rows = result.get('values', [])
        
        users = []
        for i, row in enumerate(rows):
            if i == 0: continue
            # Check if row has enough columns (User, Loc, Time, Status)
            if len(row) >= 4 and row[3] == 'ACTIVE':
                users.append({
                    'user_id': row[0],
                    'location': row[1]
                })
        return users
        
    except Exception as e:
        print(f"Get Users Error: {e}", file=sys.stderr)
        return []
