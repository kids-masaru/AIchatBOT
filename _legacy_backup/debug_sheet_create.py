from utils.auth import get_google_credentials, get_shared_folder_id
from googleapiclient.discovery import build
import sys
from dotenv import load_dotenv
load_dotenv()

print("Debugging Config Sheet Creation...")
try:
    folder_id = get_shared_folder_id()
    print(f"Folder ID: {folder_id}")
    
    creds = get_google_credentials()
    if not creds:
        print("No Credentials!")
        sys.exit(1)
        
    drive_service = build('drive', 'v3', credentials=creds)
    
    # 1. Search
    query = "name = 'KOTO_CONFIG' and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false"
    if folder_id:
        query += f" and '{folder_id}' in parents"
    
    print(f"Query: {query}")
    results = drive_service.files().list(
        q=query, pageSize=1, supportsAllDrives=True, includeItemsFromAllDrives=True
    ).execute()
    
    files = results.get('files', [])
    print(f"Found Files: {files}")
    
    if not files:
        print("Creating new sheet...")
        file_metadata = {
            'name': 'KOTO_CONFIG',
            'mimeType': 'application/vnd.google-apps.spreadsheet'
        }
        if folder_id:
            file_metadata['parents'] = [folder_id]
            
        file = drive_service.files().create(
            body=file_metadata, fields='id', supportsAllDrives=True
        ).execute()
        print(f"Created ID: {file.get('id')}")

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Error: {e}")
