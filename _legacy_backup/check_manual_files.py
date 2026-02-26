
import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())

from tools.google_ops import search_drive
from googleapiclient.discovery import build
from utils.auth import get_google_credentials

def list_manual_files():
    # 1. Provide credentials
    creds = get_google_credentials()
    if not creds:
        print("Error: No credentials found.")
        return

    service = build('drive', 'v3', credentials=creds)

    # 2. Find "M.マニュアル" folder
    # We search for folders with exact name match
    results = service.files().list(
        q="name = 'M.マニュアル' and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
        fields="files(id, name, parents)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
    
    folders = results.get('files', [])
    if not folders:
        print("Folder 'M.マニュアル' not found.")
        # Fallback: Search for 'マニュアル'
        print("Retrying with 'マニュアル'...")
        results = service.files().list(
            q="name contains 'マニュアル' and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
            fields="files(id, name, parents)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        folders = results.get('files', [])
        
    if not folders:
        print("Folder not found.")
        return

    target_folder = folders[0]
    folder_id = target_folder['id']
    print(f"Found Folder: {target_folder['name']} ({folder_id})")

    # 3. List files inside
    # We want to see filename patterns
    query = f"'{folder_id}' in parents and trashed = false"
    
    # Pagination loop could be added but let's get first 100
    file_results = service.files().list(
        q=query,
        pageSize=100,
        fields="files(id, name, mimeType, createdTime)",
        orderBy="name",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
    
    files = file_results.get('files', [])
    print(f"Found {len(files)} files/folders inside.")
    
    print("\n--- File List ---")
    for f in files:
        print(f"[{f['mimeType']}] {f['name']} (Created: {f.get('createdTime')})")

if __name__ == "__main__":
    list_manual_files()
