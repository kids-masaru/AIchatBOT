"""
Google Sheets-based configuration storage for KOTO
This replaces local file storage to enable cloud persistence.
"""
import json
import sys
from googleapiclient.discovery import build
from utils.auth import get_google_credentials, get_shared_folder_id

CONFIG_SHEET_NAME = "KOTO_CONFIG"

DEFAULT_CONFIG = {
    # --- Global Settings ---
    "user_name": "井崎さん",
    "user_birthday": "1980-01-01",  # For horoscope/age context

    # --- 1. KOTO (Secretary & Controller) ---
    "koto_personality": "元気な秘書",
    "koto_master_prompt": "",
    "koto_tone": "Polite but friendly",

    # --- 2. SHIORI (Profiler - The Biographer) ---
    "shiori_instruction": """
    あなたは「栞（しおり）」という名の、心優しい伝記作家です。
    対象人物（ユーザー）の会話記録（Log）を読み、現在の人物プロファイル（Profile）を更新してください。
    
    【指示】
    1. 新しい会話から読み取れる「性格」「興味関心」「価値観」「悩み」「目標」を抽出してください。
    2. 現在のプロファイルと矛盾する場合は、新しい情報を優先して書き換えてください。
    3. 以前の情報で、変わっていない部分は維持してください。
    4. 出力は必ず指定されたJSON形式のみで行ってください。
    """,

    # --- 3. FUMI (Maker - The Writer) ---
    "fumi_instruction": """
    あなたは「フミ (Fumi)」です。資料作成の専門家として振る舞ってください。
    ユーザーの依頼に基づき、Google Drive内の情報を調査し、高品質なドキュメントを作成します。
    嘘の情報（ハルシネーション）を書かないように注意し、不明な点は正直に不明と伝えてください。
    """,

    # --- 4. AKI (Librarian - The Organizer) ---
    "aki_instruction": """
    あなたは「アキ (Aki)」です。整理整頓が得意な司書です。
    Google Driveのフォルダ構造を整理したり、新しい資料を適切な場所に格納したりするのがあなたの仕事です。
    ファイル名が乱雑な場合は、内容に基づいて分かりやすい名前に変更する提案をしてください。
    """,

    # --- 5. RINA (Scheduler - The Planner) ---
    "rina_instruction": """
    あなたは「リナ (Rina)」です。時間管理のプロフェッショナルです。
    ユーザーのカレンダーとタスクを分析し、最適なスケジューリングを提案してください。
    """,

    # --- 6. TOKI (History Expert - The Historian) ---
    "toki_instruction": "過去の大量のログから文脈を読み解く専門家「トキ」としての指示。",

    # --- 7. REN (Comms Expert - The Communicator) ---
    "ren_instruction": "メールやメッセージのドラフト作成、返信推奨を行う専門家「レン」としての指示。",

    # --- Resources ---
    "knowledge_sources": [],
    "reminders": [
        {
            "name": "Morning Briefing",
            "time": "07:00",
            "prompt": "今日の天気、今日・明日・今週の予定とタスクを確認して、まとめて教えて！最後に今日も頑張ろうという気持ちになる一言をお願い！",
            "enabled": True
        },
        {
            "name": "Evening Check-in",
            "time": "18:00",
            "prompt": "今日の業務の振り返りをして。まだ残っているタスクがないか確認して。明日の予定も軽く教えて。",
            "enabled": True
        }
    ],
    "notion_databases": []
}

_config_sheet_id = None  # Cache

def get_or_create_config_sheet():
    """Get or create the KOTO_CONFIG spreadsheet in the shared folder"""
    global _config_sheet_id
    if _config_sheet_id:
        return _config_sheet_id
    
    try:
        creds = get_google_credentials()
        if not creds:
            print("Auth failed in sheets_config", file=sys.stderr)
            return None
            
        drive_service = build('drive', 'v3', credentials=creds)
        sheets_service = build('sheets', 'v4', credentials=creds)
        
        folder_id = get_shared_folder_id()
        
        # Search for existing config sheet
        query = f"name = '{CONFIG_SHEET_NAME}' and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false"
        if folder_id:
            print(f"DEBUG: Searching for config in Shared Folder: {folder_id}", file=sys.stdout)
            query += f" and '{folder_id}' in parents"
        else:
            print(f"WARNING: No GOOGLE_DRIVE_FOLDER_ID found. Searching globally.", file=sys.stdout)
            
        results = drive_service.files().list(
            q=query,
            pageSize=1,
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        
        files = results.get('files', [])
        
        if files:
            _config_sheet_id = files[0]['id']
            print(f"DEBUG: Found existing config sheet: {_config_sheet_id} (Name: {files[0]['name']})", file=sys.stdout)
            return _config_sheet_id
        
        # Create new spreadsheet
        file_metadata = {
            'name': CONFIG_SHEET_NAME,
            'mimeType': 'application/vnd.google-apps.spreadsheet'
        }
        if folder_id:
            file_metadata['parents'] = [folder_id]
            
        file = drive_service.files().create(
            body=file_metadata,
            fields='id',
            supportsAllDrives=True
        ).execute()
        
        _config_sheet_id = file.get('id')
        print(f"Created new config sheet: {_config_sheet_id}", file=sys.stderr)
        
        # Initialize with default config
        save_config(DEFAULT_CONFIG)
        
        return _config_sheet_id
        
    except Exception as e:
        print(f"CRITICAL ERROR in get_or_create_config_sheet: {e}", file=sys.stdout)
        import traceback
        traceback.print_exc()
        return None

def load_config():
    """Load configuration from Google Sheets"""
    try:
        sheet_id = get_or_create_config_sheet()
        if not sheet_id:
            return DEFAULT_CONFIG
            
        creds = get_google_credentials()
        if not creds:
            return DEFAULT_CONFIG
            
        sheets_service = build('sheets', 'v4', credentials=creds)
        
        # Read from A1 (JSON string stored there)
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range='A1'
        ).execute()
        
        values = result.get('values', [])
        if values and values[0]:
            config_json = values[0][0]
            config = json.loads(config_json)
            # Merge with defaults to handle missing keys
            # Merge with defaults to handle missing keys
            merged = {**DEFAULT_CONFIG, **config}
            print(f"DEBUG: Config loaded from sheet {_config_sheet_id}. Keys found: {list(config.keys())}", file=sys.stdout)
            return merged
        else:
            print(f"DEBUG: Sheet {_config_sheet_id} was empty or invalid structure. Using defaults.", file=sys.stdout)
            return DEFAULT_CONFIG
            
    except Exception as e:
        print(f"CRITICAL ERROR loading config from sheets: {e}", file=sys.stdout)
        return DEFAULT_CONFIG

def save_config(config):
    """Save configuration to Google Sheets"""
    try:
        sheet_id = get_or_create_config_sheet()
        if not sheet_id:
            return False
            
        creds = get_google_credentials()
        if not creds:
            return False
            
        sheets_service = build('sheets', 'v4', credentials=creds)
        
        # Store as JSON string in A1
        config_json = json.dumps(config, ensure_ascii=False, indent=2)
        
        sheets_service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range='A1',
            valueInputOption='RAW',
            body={'values': [[config_json]]}
        ).execute()
        
        print(f"Config saved to sheet {sheet_id}", file=sys.stderr)
        return True
        
    except Exception as e:
        print(f"Error saving config to sheets: {e}", file=sys.stderr)
        return False
