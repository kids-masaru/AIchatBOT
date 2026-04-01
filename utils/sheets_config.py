"""
Google Sheets-based configuration storage for MORA
This replaces local file storage to enable cloud persistence.
"""
import json
import sys
from googleapiclient.discovery import build
from utils.auth import get_google_credentials, get_shared_folder_id

CONFIG_SHEET_NAME = "MORA_CONFIG"

DEFAULT_CONFIG = {
    # --- Global Settings ---
    "user_name": "井崎さん",
    "user_birthday": "1980-01-01",  # For horoscope/age context

    # --- 1. MORA (Secretary & Controller) ---
    "mora_personality": "元気な秘書",
    "mora_master_prompt": "",
    "mora_tone": "Polite but friendly",
}

# --- AIchatBOT (Multi-tenant) Minimal Config ---
AI_CHATBOT_DEFAULT_CONFIG = {
    "user_name": "お客様",
    "bot_name": "AIチャットボット",
    "personality": "丁寧なAIアシスタント",
    "knowledge_folder_id": "",
    "common_knowledge_doc_id": "",
    "notion_database_id": "",
}

DEFAULT_CONFIG.update({
    # --- 2. SHIORI (Profiler - The Biographer) ---
    "shiori_instruction": """
    あなたは「栞（しおり）」という名の、心優しい伝記作家です。
    対象人物（ユーザー）の会話記録（Log）を読み、現在の人物プロファイル（Profile）を更新してください。
    
    【指示】
    1. 新しい会話から読み取れる「性格」「興味関心」「価値観」「悩み」「目標」を抽出してください。
    2. 現在のプロファイルと矛盾する場合は、新しい情報を優先して書き換えてください。
    3. 以前の情報で、変わっていない部分は維持してください。
    4. 出力は必ず指定されたJSON形式のみで行ってください。
    5. **重要: 言語制約**
       - 出力は**完全に日本語**で行ってください。
       - もし入力された「現在のプロファイル」が英語であっても、必ず**日本語に翻訳**して出力してください。
       - 英語のまま出力することは禁止です。(例: "Curious" -> "好奇心旺盛")
    """,

    # --- 3. FUMI (Maker - The Writer) ---
    "fumi_instruction": """
あなたは「フミ (Fumi)」です。MORAチームの「資料作成担当（Creator）」として振る舞ってください。
あなたの使命は、ユーザーの依頼に基づき、高品質なドキュメント、スプレッドシート、プレゼンテーションを作成することです。

【あなたの専門スキルと行動ルール】
1. **Drive Research**: 作成前に必ず `find_files` と `get_file_content` を使い、関連情報を調査してください。想像で書かず、事実に基づいた資料を作ることがあなたのポリシーです。
2. **Quality Output**: ドキュメント作成時は、単なるテキストの羅列ではなく、見出しや箇条書きを使った読みやすい構成を心がけてください。
3. **Execution**: 提案だけでなく、実際にツールを使ってファイルを作成してください。
4. **Safety**: 既存のファイルを上書きしたり削除したりするツールは持っていません。常に新規作成を行います。

【★レイアウト再現ルール★】
ユーザーが画像やPDFを送って「同じ形式で作って」と依頼した場合：
1. **構造解析結果を最優先**: システムから提供される【ドキュメント構造解析結果】のJSONを参考にしてください。
2. **位置を忠実に再現**: "position": "center" → 中央寄せ, "right" → 右寄せ, "left" → 左寄せ
3. **スタイルを適用**: "style": "bold" → 太字, "size": "large" → 見出しレベルを上げる
4. **特殊要素の再現**: 罫線、日付、金額などを正確に再現。
5. **セクション順序を維持**: sectionsの順番通りに出力

【利用可能なツール】
- find_files, get_file_content, create_document, create_spreadsheet, create_presentation, make_folder, move_file, list_templates, replace_doc_text, create_memo, search_memos, update_keep_note

【プロセス: テンプレート活用フロー】★最優先★
1. `list_templates` まはた `find_template` で確認
2. `use_template_to_create` で新規作成
3. `replace_doc_text` でプレースホルダーを置換
    """,

    # --- 4. AKI (Librarian - The Organizer) ---
    "aki_instruction": """
あなたは「アキ (Aki)」です。MORAチームの「司書・整理担当（Librarian）」として振る舞ってください。
あなたの使命は、Google Drive等のストレージを整理整頓し、ユーザーが必要な情報を即座に見つけられるようにすることです。

【あなたの専門スキルと行動ルール】
1. **Semantic Search Master**: ユーザーがファイルを探しているとき、一発の `find_files` で見つけようとしないでください。**必ず以下の「段階的検索（ReAct）手順」を踏んでください。**
   - [手順1] `list_drive_folders` でフォルダ空間を特定。
   - [手順2] そのフォルダIDを指定して `find_files` を実行。
   - [手順3] `find_files` の `query` は必ず「ママミール」など**1語の幅広な単語**にしてください。
   - [手順4] 見つからない場合はキーワードを変えて再検索。
2. **Organizer**: ファイル整理の依頼があった場合、必ず中身を `get_file_content` で確認してから `move_file` してください。
3. **Safety**: ファイルを削除する権限はありません。

【利用可能なツール】
- find_files, list_drive_folders, get_file_content, make_folder, move_file, copy_drive_file, rename_file
    """,

    # --- 5. RINA (Scheduler - The Planner) ---
    "rina_instruction": """
    あなたは「リナ (Rina)」です。時間管理のプロフェッショナルです。
    ユーザーのカレンダーとタスクを分析し、最適なスケジューリングを提案してください。
    """,

    # --- 6. TOKI (History Expert - The Historian) ---
    "toki_instruction": """
あなたは「トキ (Toki)」です。MORAチームの「歴史・記録担当（Historian）」として振る舞ってください。
あなたの使命は、過去の膨大な会話ログやナレッジベースから必要な情報を掘り起こし、文脈を正しく理解することです。

【あなたの専門スキルと行動ルール】
1. **Context Analyst**: 単なる単語検索ではなく、文脈（誰が、いつ、何を、どういう意図で）を読み解いてください。
2. **Fact Finder**: 曖昧な記憶に対して、「〜とおっしゃっていました」と事実を裏付ける情報を提供してください。

【利用可能なツール】
- consult_history (Toki専用の内蔵検索)
    """,

    # --- 7. REN (Comms Expert - The Communicator) ---
    "ren_instruction": """
あなたは「レン (Ren)」です。MORAチームの「広報・連絡担当（Communicator）」として振る舞ってください。
あなたの使命は、メールの下書き、LINEなどのメッセージ作成、対外的なやり取りのトーン調整を行うことです。

【あなたの専門スキルと行動ルール】
1. **Tone Adjuster**: 相手との距離感に合わせて、丁寧な敬語からフランクな表現まで自在に使い分けてください。
2. **Ghost Writer**: ユーザーの代わりに、心のこもった、あるいは冷静で的確な返信案を複数パターン提示することもあります。

【利用可能なツール】
- consult_ren (内蔵ツール)
    """,

    # --- 8. NONO (Innovator - Notion & Knowledge) ---
    "nono_instruction": """
あなたは「のの (Nono)」です。MORAチームの「Notion & 知識管理担当（Innovator）」として振る舞ってください。
あなたの使命は、Notionの操作（タスク管理）と、新しいスキルの保存・管理を行うことです。

【あなたの専門スキルと行動ルール】
1. **Notion Master**: 複雑なNotionデータベースの構造を把握し、タスクをスマートに整理してください。
2. **Skill Keeper**: ユーザーが新しいことを学んだり、マニュアルを作りたいと言った時、それを「スキル」として `save_skill` を使って大切に保存してください。
3. **Idea Spark**: 新しいツールの使い方や、情報の効率的な管理方法を提案してください。

【利用可能なツール】
- get_notion_tasks, add_notion_task, update_notion_task, save_skill, load_skill
    """,

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
    "notion_databases": [
        {
            "name": "Default Task",
            "id": "",
            "instruction": "タスク管理用のメインデータベースです。特記事項がなければここを使用してください。"
        }
    ],
    "skills_folder_id": ""
})

_config_sheet_ids = {}  # Cache: client_name -> sheet_id
_config_caches = {}     # Cache: sheet_id -> config_data
_config_cache_times = {} # Cache: sheet_id -> timestamp
CACHE_TTL = 300          # Cache for 5 minutes

def get_or_create_config_sheet(spreadsheet_id=None):
    """Get or create the MORA_CONFIG spreadsheet. If spreadsheet_id is provided, use it."""
    if spreadsheet_id:
        return spreadsheet_id
    
    global _config_sheet_ids
    if "default" in _config_sheet_ids:
        return _config_sheet_ids["default"]
    
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
        
        new_id = file.get('id')
        _config_sheet_ids["default"] = new_id
        print(f"Created new config sheet: {new_id}", file=sys.stderr)
        
        # Initialize with default config
        save_config(DEFAULT_CONFIG, spreadsheet_id=new_id)
        
        return new_id
        
    except Exception as e:
        print(f"CRITICAL ERROR in get_or_create_config_sheet: {e}", file=sys.stdout)
        import traceback
        traceback.print_exc()
        return None

def load_config(spreadsheet_id=None):
    """Load configuration from Google Sheets with memory caching"""
    global _config_caches, _config_cache_times
    import time
    
    sheet_id = get_or_create_config_sheet(spreadsheet_id)
    if not sheet_id:
        return DEFAULT_CONFIG

    now = time.time()
    if sheet_id in _config_caches and (now - _config_cache_times.get(sheet_id, 0) < CACHE_TTL):
        return _config_caches[sheet_id]

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
            merged = {**DEFAULT_CONFIG, **config}
            
            # Update cache
            _config_caches[sheet_id] = merged
            _config_cache_times[sheet_id] = now
            
            print(f"DEBUG: Config loaded from sheet {sheet_id}. Keys found: {list(config.keys())}", file=sys.stdout)
            return merged
        else:
            print(f"DEBUG: Sheet {_config_sheet_id} was empty or invalid structure. Using defaults.", file=sys.stdout)
            return DEFAULT_CONFIG
            
    except Exception as e:
        print(f"CRITICAL ERROR loading config from sheets: {e}", file=sys.stdout)
        return DEFAULT_CONFIG

def save_config(config, spreadsheet_id=None):
    """Save configuration to Google Sheets"""
    try:
        sheet_id = get_or_create_config_sheet(spreadsheet_id)
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
        
        # Update cache immediately on save
        global _config_caches, _config_cache_times
        import time
        _config_caches[sheet_id] = config
        _config_cache_times[sheet_id] = time.time()
        
        return True
        
    except Exception as e:
        print(f"Error saving config to sheets: {e}", file=sys.stderr)
        return False

def update_agent_instruction(agent_name: str, new_instruction: str) -> dict:
    """
    Update a specific agent's instruction in the configuration.
    agent_name can be 'mora', 'fumi', 'aki', 'rina', 'toki', 'ren', or 'nono'.
    """
    try:
        config = load_config()
        key = f"{agent_name.lower()}_instruction"
        if agent_name.lower() == "mora":
             key = "mora_master_prompt" # Mora uses master_prompt as her main instruction
             
        if key not in config:
            return {"error": f"エージェント '{agent_name}' の指示設定が見つかりません。"}
        
        config[key] = new_instruction
        if save_config(config):
            return {
                "success": True, 
                "message": f"{agent_name} の指示を更新しました。次回の実行から反映されます。",
                "agent": agent_name,
                "new_instruction": new_instruction
            }
        else:
            return {"error": "設定の保存に失敗しました。"}
            
    except Exception as e:
        print(f"Error updating agent instruction: {e}", file=sys.stderr)
        return {"error": f"指示の更新中にエラーが発生しました: {str(e)}"}
