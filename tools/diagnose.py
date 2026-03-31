"""
Diagnostic script for Mora AI Secretary
Checks environment variables and API connectivity
"""
import os
import sys
import json
import urllib.request
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Load environment variables from .env file
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_env_vars():
    print("=== Environment Variables Check ===")
    required_vars = [
        'GEMINI_API_KEY',
        'GOOGLE_SERVICE_ACCOUNT_KEY',
        'GOOGLE_DRIVE_FOLDER_ID',
        'LINE_CHANNEL_SECRET',
        'LINE_CHANNEL_ACCESS_TOKEN'
    ]
    
    all_ok = True
    for var in required_vars:
        value = os.environ.get(var)
        if value:
            masked = value[:4] + '****' + value[-4:] if len(value) > 8 else '****'
            print(f"✅ {var}: Found ({masked})")
        else:
            print(f"❌ {var}: Missing")
            all_ok = False
            
    return all_ok

def check_google_auth():
    print("\n=== Google Service Account Check ===")
    key_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_KEY')
    if not key_json:
        print("❌ No Service Account Key found")
        return False
        
    try:
        info = json.loads(key_json)
        print(f"✅ JSON Parse: OK (Project ID: {info.get('project_id')})")
        print(f"✅ Client Email: {info.get('client_email')}")
        
        credentials = service_account.Credentials.from_service_account_info(
            info,
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        print("✅ Credentials Object: Created")
        return True
    except Exception as e:
        print(f"❌ Auth Error: {e}")
        return False

def check_drive_access():
    print("\n=== Google Drive API Access Check ===")
    try:
        key_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_KEY')
        info = json.loads(key_json)
        credentials = service_account.Credentials.from_service_account_info(
            info,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        
        service = build('drive', 'v3', credentials=credentials)
        
        # Try to list files
        results = service.files().list(pageSize=1).execute()
        files = results.get('files', [])
        print(f"✅ Drive List: OK (Found {len(files)} files)")
        
        # Check Shared Folder Access if ID exists
        folder_id = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
        if folder_id:
            try:
                # supportsAllDrives=True is required for Shared Drives
                folder = service.files().get(
                    fileId=folder_id,
                    supportsAllDrives=True
                ).execute()
                print(f"✅ Shared Folder Access: OK (Name: {folder.get('name')})")
            except Exception as e:
                print(f"❌ Shared Folder Access Error: {e}")
                print("   Note: The Service Account might not have permission for this folder.")
        
        return True
    except Exception as e:
        print(f"❌ Drive API Error: {e}")
        return False

def check_gemini_access():
    print("\n=== Gemini API Check ===")
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print("❌ No API Key")
        return False
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": "Hello"}]}]}
    
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        with urllib.request.urlopen(req) as res:
            if res.status == 200:
                print("✅ Gemini API: OK")
                return True
            else:
                print(f"❌ Gemini API Status: {res.status}")
                return False
    except Exception as e:
        print(f"❌ Gemini API Error: {e}")
        return False

if __name__ == "__main__":
    print("Starting Mora Diagnostics...\n")
    check_env_vars()
    check_google_auth()
    check_drive_access()
    check_gemini_access()
    print("\nDiagnostics Complete.")
