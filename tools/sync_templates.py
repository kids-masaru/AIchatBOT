"""
Script to sync template registry with actual folder contents.
"""
from tools.template_ops import list_templates, get_or_create_template_registry, scan_for_placeholders
from googleapiclient.discovery import build
from utils.auth import get_google_credentials

def sync_registry():
    print("Starting template registry sync...")
    
    # 1. Get actual files
    folder_result = list_templates()
    if folder_result.get("error"):
        print(f"Error listing files: {folder_result['error']}")
        return
        
    actual_files = folder_result.get("templates", [])
    print(f"Found {len(actual_files)} actual templates in folder.")
    
    # 2. Get registry sheet
    registry_result = get_or_create_template_registry()
    if registry_result.get("error"):
        print(f"Error getting registry: {registry_result['error']}")
        return
        
    sheet_id = registry_result["sheet_id"]
    creds = get_google_credentials()
    service = build('sheets', 'v4', credentials=creds)
    
    # 3. Clear existing registry (except header)
    service.spreadsheets().values().clear(
        spreadsheetId=sheet_id,
        range='Registry!A2:G1000'
    ).execute()
    print("Cleared old registry entries.")
    
    # 4. Register actual files
    new_rows = []
    import datetime
    now = datetime.datetime.now().isoformat()
    
    for tmpl in actual_files:
        print(f"Processing: {tmpl['name']} (ID: {tmpl['id']})")
        
        # Scan fields
        scan_result = scan_for_placeholders(tmpl['id'])
        fields = scan_result.get('fields', [])
        print(f"  - Detected fields: {fields}")
        
        # Guess type from name
        t_type = "その他"
        if "領収" in tmpl['name']: t_type = "領収書"
        elif "請求" in tmpl['name']: t_type = "請求書"
        elif "見積" in tmpl['name']: t_type = "見積書"
        elif "議事" in tmpl['name']: t_type = "議事録"
        
        description = f"自動登録されたテンプレート: {tmpl['name']}"
        usage_hint = f"{tmpl['name']}を作成したい時に使用"
        
        new_rows.append([
            tmpl['id'],
            tmpl['name'],
            t_type,
            description,
            ','.join(fields),
            usage_hint,
            now
        ])
        
    if new_rows:
        service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range='Registry!A2',
            valueInputOption='RAW',
            body={'values': new_rows}
        ).execute()
        print(f"Successfully registered {len(new_rows)} templates.")
    else:
        print("No templates to register.")

if __name__ == "__main__":
    sync_registry()
