"""
Google authentication utilities
"""
import os
import sys
import json
from google.oauth2 import service_account
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Google Workspace credentials
# Try both common variable names
GOOGLE_SERVICE_ACCOUNT_KEY = os.environ.get('GOOGLE_SERVICE_ACCOUNT_KEY') or os.environ.get('GOOGLE_CREDENTIALS', '{}')
GOOGLE_DELEGATED_USER = os.environ.get('GOOGLE_DELEGATED_USER', '')
GOOGLE_DRIVE_FOLDER_ID = os.environ.get('GOOGLE_DRIVE_FOLDER_ID', '')

# Google API scopes
SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/presentations',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.compose',  # For creating drafts
    'https://www.googleapis.com/auth/forms',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/tasks',
]


def get_google_credentials():
    """Get Google credentials with domain-wide delegation"""
    try:
        service_account_info = json.loads(GOOGLE_SERVICE_ACCOUNT_KEY)
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=SCOPES
        )
        if GOOGLE_DELEGATED_USER:
            credentials = credentials.with_subject(GOOGLE_DELEGATED_USER)
        return credentials
    except Exception as e:
        print(f"Credentials error: {e}", file=sys.stderr)
        return None


def get_shared_folder_id():
    """Get the shared folder ID from environment"""
    return GOOGLE_DRIVE_FOLDER_ID
