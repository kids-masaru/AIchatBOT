"""
Template Operations - Dynamic Template System
Manages templates in Google Drive with auto-recognition and learning.
"""
import os
import sys
import json
from googleapiclient.discovery import build
from utils.auth import get_google_credentials, get_shared_folder_id

# Template folder name in Drive
TEMPLATE_FOLDER_NAME = "MORA_TEMPLATES"
# Registry sheet name
TEMPLATE_REGISTRY_NAME = "MORA_TEMPLATE_REGISTRY"


def get_or_create_template_folder() -> dict:
    """
    Get the template folder ID, creating it if it doesn't exist.
    
    Returns:
        Dictionary with folder_id and status
    """
    try:
        creds = get_google_credentials()
        if not creds:
            return {"error": "Google認証に失敗しました。"}
        
        drive_service = build('drive', 'v3', credentials=creds)
        parent_folder_id = get_shared_folder_id()
        
        # Search for existing template folder
        query = f"name = '{TEMPLATE_FOLDER_NAME}' and mimeType = 'application/vnd.google-apps.folder' and '{parent_folder_id}' in parents and trashed = false"
        results = drive_service.files().list(
            q=query,
            fields='files(id, name)',
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        
        files = results.get('files', [])
        
        if files:
            folder_id = files[0]['id']
            print(f"Template folder found: {folder_id}", file=sys.stderr)
            return {"success": True, "folder_id": folder_id, "status": "existing"}
        
        # Create new template folder
        folder_metadata = {
            'name': TEMPLATE_FOLDER_NAME,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_folder_id]
        }
        
        folder = drive_service.files().create(
            body=folder_metadata,
            fields='id',
            supportsAllDrives=True
        ).execute()
        
        folder_id = folder.get('id')
        print(f"Template folder created: {folder_id}", file=sys.stderr)
        return {"success": True, "folder_id": folder_id, "status": "created"}
        
    except Exception as e:
        print(f"Template folder error: {e}", file=sys.stderr)
        return {"error": f"テンプレートフォルダの取得/作成に失敗: {str(e)}"}


def list_templates() -> dict:
    """
    List all templates in the template folder.
    
    Returns:
        Dictionary with list of templates
    """
    try:
        folder_result = get_or_create_template_folder()
        if folder_result.get("error"):
            return folder_result
        
        folder_id = folder_result["folder_id"]
        
        creds = get_google_credentials()
        drive_service = build('drive', 'v3', credentials=creds)
        
        # List files in template folder
        query = f"'{folder_id}' in parents and trashed = false"
        results = drive_service.files().list(
            q=query,
            fields='files(id, name, mimeType, modifiedTime)',
            orderBy='name',
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        
        files = results.get('files', [])
        
        templates = [
            {
                "id": f.get('id'),
                "name": f.get('name'),
                "type": f.get('mimeType'),
                "modified": f.get('modifiedTime')
            }
            for f in files
        ]
        
        return {"success": True, "count": len(templates), "templates": templates}
        
    except Exception as e:
        print(f"List templates error: {e}", file=sys.stderr)
        return {"error": f"テンプレート一覧取得に失敗: {str(e)}"}


def get_or_create_template_registry() -> dict:
    """
    Get or create the template registry spreadsheet.
    
    Returns:
        Dictionary with sheet_id
    """
    try:
        creds = get_google_credentials()
        if not creds:
            return {"error": "Google認証に失敗しました。"}
        
        drive_service = build('drive', 'v3', credentials=creds)
        sheets_service = build('sheets', 'v4', credentials=creds)
        parent_folder_id = get_shared_folder_id()
        
        # Search for existing registry
        query = f"name = '{TEMPLATE_REGISTRY_NAME}' and mimeType = 'application/vnd.google-apps.spreadsheet' and '{parent_folder_id}' in parents and trashed = false"
        results = drive_service.files().list(
            q=query,
            fields='files(id, name)',
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        
        files = results.get('files', [])
        
        if files:
            sheet_id = files[0]['id']
            print(f"Template registry found: {sheet_id}", file=sys.stderr)
            return {"success": True, "sheet_id": sheet_id, "status": "existing"}
        
        # Create new registry spreadsheet
        spreadsheet = {
            'properties': {'title': TEMPLATE_REGISTRY_NAME},
            'sheets': [{
                'properties': {'title': 'Registry'},
                'data': [{
                    'startRow': 0,
                    'startColumn': 0,
                    'rowData': [{
                        'values': [
                            {'userEnteredValue': {'stringValue': 'file_id'}},
                            {'userEnteredValue': {'stringValue': 'name'}},
                            {'userEnteredValue': {'stringValue': 'type'}},
                            {'userEnteredValue': {'stringValue': 'description'}},
                            {'userEnteredValue': {'stringValue': 'fields'}},
                            {'userEnteredValue': {'stringValue': 'usage_hint'}},
                            {'userEnteredValue': {'stringValue': 'last_updated'}}
                        ]
                    }]
                }]
            }]
        }
        
        created = sheets_service.spreadsheets().create(body=spreadsheet).execute()
        sheet_id = created.get('spreadsheetId')
        
        # Move to shared folder
        drive_service.files().update(
            fileId=sheet_id,
            addParents=parent_folder_id,
            fields='id, parents',
            supportsAllDrives=True
        ).execute()
        
        print(f"Template registry created: {sheet_id}", file=sys.stderr)
        return {"success": True, "sheet_id": sheet_id, "status": "created"}
        
    except Exception as e:
        print(f"Template registry error: {e}", file=sys.stderr)
        return {"error": f"テンプレートレジストリの取得/作成に失敗: {str(e)}"}


def get_registered_templates() -> dict:
    """
    Get all registered templates from the registry.
    
    Returns:
        Dictionary with registered templates
    """
    try:
        registry_result = get_or_create_template_registry()
        if registry_result.get("error"):
            return registry_result
        
        sheet_id = registry_result["sheet_id"]
        
        creds = get_google_credentials()
        sheets_service = build('sheets', 'v4', credentials=creds)
        
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range='Registry!A2:G100'  # Skip header row
        ).execute()
        
        values = result.get('values', [])
        
        templates = {}
        for row in values:
            if len(row) >= 2:
                file_id = row[0] if len(row) > 0 else ''
                name = row[1] if len(row) > 1 else ''
                template_type = row[2] if len(row) > 2 else ''
                description = row[3] if len(row) > 3 else ''
                fields = row[4] if len(row) > 4 else ''
                usage_hint = row[5] if len(row) > 5 else ''
                last_updated = row[6] if len(row) > 6 else ''
                
                templates[file_id] = {
                    "file_id": file_id,
                    "name": name,
                    "type": template_type,
                    "description": description,
                    "fields": fields.split(',') if fields else [],
                    "usage_hint": usage_hint,
                    "last_updated": last_updated
                }
        
        return {"success": True, "templates": templates}
        
    except Exception as e:
        print(f"Get registered templates error: {e}", file=sys.stderr)
        return {"error": f"登録済みテンプレート取得に失敗: {str(e)}"}


def register_template(file_id: str, name: str, template_type: str, 
                      description: str, fields: list, usage_hint: str) -> dict:
    """
    Register a template in the registry.
    
    Args:
        file_id: Google Drive file ID
        name: Template name
        template_type: Type of document (領収書, 議事録, etc.)
        description: Description of the template
        fields: List of fields to fill in
        usage_hint: Hint for when to use this template
        
    Returns:
        Dictionary with registration result
    """
    try:
        registry_result = get_or_create_template_registry()
        if registry_result.get("error"):
            return registry_result
        
        sheet_id = registry_result["sheet_id"]
        
        creds = get_google_credentials()
        sheets_service = build('sheets', 'v4', credentials=creds)
        
        import datetime
        now = datetime.datetime.now().isoformat()
        
        # Append new row
        values = [[
            file_id,
            name,
            template_type,
            description,
            ','.join(fields) if fields else '',
            usage_hint,
            now
        ]]
        
        sheets_service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range='Registry!A:G',
            valueInputOption='RAW',
            body={'values': values}
        ).execute()
        
        print(f"Template registered: {name}", file=sys.stderr)
        return {
            "success": True,
            "message": f"テンプレート「{name}」を登録しました。",
            "template": {
                "file_id": file_id,
                "name": name,
                "type": template_type,
                "fields": fields
            }
        }
        
    except Exception as e:
        print(f"Register template error: {e}", file=sys.stderr)
        return {"error": f"テンプレート登録に失敗: {str(e)}"}


def check_unregistered_templates() -> dict:
    """
    Check for templates in the folder that are not yet registered.
    
    Returns:
        Dictionary with unregistered templates
    """
    try:
        # Get all templates in folder
        folder_result = list_templates()
        if folder_result.get("error"):
            return folder_result
        
        folder_templates = {t["id"]: t for t in folder_result.get("templates", [])}
        
        # Get registered templates
        registry_result = get_registered_templates()
        if registry_result.get("error"):
            return registry_result
        
        registered = registry_result.get("templates", {})
        
        # Find unregistered
        unregistered = []
        for file_id, template in folder_templates.items():
            if file_id not in registered:
                unregistered.append(template)
        
        return {
            "success": True,
            "unregistered_count": len(unregistered),
            "unregistered": unregistered,
            "registered_count": len(registered)
        }
        
    except Exception as e:
        print(f"Check unregistered error: {e}", file=sys.stderr)
        return {"error": f"未登録テンプレート確認に失敗: {str(e)}"}


def copy_template(template_file_id: str, new_name: str) -> dict:
    """
    Copy a template file to create a new document.
    
    Args:
        template_file_id: File ID of the template
        new_name: Name for the new document
        
    Returns:
        Dictionary with new file info
    """
    try:
        creds = get_google_credentials()
        if not creds:
            return {"error": "Google認証に失敗しました。"}
        
        drive_service = build('drive', 'v3', credentials=creds)
        parent_folder_id = get_shared_folder_id()
        
        # Copy the file
        copied_file = drive_service.files().copy(
            fileId=template_file_id,
            body={
                'name': new_name,
                'parents': [parent_folder_id]
            },
            supportsAllDrives=True
        ).execute()
        
        file_id = copied_file.get('id')
        
        # Get the web view link
        file_info = drive_service.files().get(
            fileId=file_id,
            fields='webViewLink',
            supportsAllDrives=True
        ).execute()
        
        return {
            "success": True,
            "file_id": file_id,
            "name": new_name,
            "url": file_info.get('webViewLink')
        }
        
    except Exception as e:
        print(f"Copy template error: {e}", file=sys.stderr)
        return {"error": f"テンプレートのコピーに失敗: {str(e)}"}


def find_template_by_type(template_type: str) -> dict:
    """
    Find a registered template by its type/purpose.
    
    Args:
        template_type: Type to search for (e.g., "領収書", "議事録")
        
    Returns:
        Dictionary with matching template or None
    """
    try:
        registry_result = get_registered_templates()
        if registry_result.get("error"):
            return registry_result
        
        templates = registry_result.get("templates", {})
        
        # Search by type or name (case-insensitive partial match)
        search_term = template_type.lower()
        
        for file_id, template in templates.items():
            if (search_term in template.get("type", "").lower() or
                search_term in template.get("name", "").lower() or
                search_term in template.get("description", "").lower()):
                return {"success": True, "found": True, "template": template}
        
        return {"success": True, "found": False, "message": f"「{template_type}」に該当するテンプレートが見つかりませんでした。"}
        
    except Exception as e:
        print(f"Find template error: {e}", file=sys.stderr)
        return {"error": f"テンプレート検索に失敗: {str(e)}"}


def scan_for_placeholders(file_id: str) -> dict:
    """
    Scan a Google Doc for placeholders like {{name}}.
    
    Args:
        file_id: The ID of the file to scan
        
    Returns:
        Dictionary with list of detected fields
    """
    try:
        from tools.google_ops import read_drive_file
        content_result = read_drive_file(file_id)
        
        if content_result.get("error"):
            return content_result
        
        text = content_result.get("content", "")
        
        import re
        # Find all {{...}} patterns
        matches = re.findall(r'\{\{(.+?)\}\}', text)
        
        # Unique fields, strip whitespace
        fields = sorted(list(set([m.strip() for m in matches])))
        
        return {
            "success": True, 
            "fields": fields,
            "count": len(fields)
        }
        
    except Exception as e:
        print(f"Scan placeholders error: {e}", file=sys.stderr)
        return {"error": f"プレースホルダー解析に失敗: {str(e)}"}


def replace_placeholders(file_id: str, replacements: dict) -> dict:
    """
    Replace placeholders in a Google Doc with actual values.
    Uses batchUpdate to preserve formatting.
    
    Args:
        file_id: The ID of the file to update
        replacements: Dictionary of {key: value} (e.g., {"宛名": "田中様"})
        
    Returns:
        Dictionary with update result
    """
    try:
        creds = get_google_credentials()
        if not creds:
            return {"error": "Google認証に失敗しました。"}
        
        # We need docs service for batchUpdate
        docs_service = build('docs', 'v1', credentials=creds)
        
        requests = []
        for key, value in replacements.items():
            # Prepare replacement text (handle None)
            replace_text = str(value) if value is not None else ""
            
            # Create regex replacement request
            # Matches {{key}}
            requests.append({
                'replaceAllText': {
                    'containsText': {
                        'text': f'{{{{{key}}}}}',
                        'matchCase': True
                    },
                    'replaceText': replace_text
                }
            })
            
        if not requests:
            return {"success": True, "message": "置換リクエストがありませんでした。"}
            
        # Execute batch update
        result = docs_service.documents().batchUpdate(
            documentId=file_id,
            body={'requests': requests}
        ).execute()
        
        return {
            "success": True,
            "message": f"{len(requests)}箇所のプレースホルダーを置換しました。",
            "replies": result.get('replies', [])
        }
        
    except Exception as e:
        print(f"Replace placeholders error: {e}", file=sys.stderr)
        return {"error": f"プレースホルダー置換に失敗: {str(e)}"}
