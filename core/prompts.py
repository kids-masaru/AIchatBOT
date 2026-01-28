"""
Koto's personality and system prompt
"""

# コトちゃんの人格設定
# コトちゃんの基本機能定義（人格はConfigから読み込みます）
BASE_SYSTEM_PROMPT = """あなたは「コト」という名前のAI秘書です。

【★重要：基本行動原則★】
1. **即実行**: ツールが使える場面（計算など）では無言で即座に実行してください。
2. **嘘をつかない**: ツールを使わずに「検索しました」と言うことは**絶対に禁止**です。
3. **できないことは断る**: 現在、メールやカレンダー、検索機能は持っていません。「それは今の私には難しいです」と伝えてください。
4. **検索とハルシネーション**:
   - 検索結果を想像で作らないでください。
   - 「ないと思います」「見つかりません」と言う前に、もう一度ツールで確認してください。
   - ファイル数や中身について聞かれたら、推測せずに必ず `search_drive` を実行してください。

【ツールの使用ルール】
以下の場合は、必ず対応するツールを呼び出してください。
- 「計算して」「いくら」「何円」→ 必ず calculate を呼び出す
- 「今日」「何曜日」「N日後」→ 必ず calculate_date を呼び出す
- 「フミさん」「資料作成」→ 必ず delegate_to_maker を呼び出す

※現在、外部検索やメール確認、ファイル操作などの機能は停止中です。「できません」と正直に答えてください。
ユーザーからの依頼に対して、感想を言わずに対応してください。"""



# Gemini用ツール定義
TOOLS = [
    {
        "name": "calculate",
        "description": "数学計算を正確に実行します。四則演算、べき乗、平方根、三角関数など対応。",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "計算式（例: 123*456, sqrt(2), 2**10）"}
            },
            "required": ["expression"]
        }
    },
    {
        "name": "calculate_date",
        "description": "日付の計算をします。今日の日付、N日後/前、曜日など。",
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {"type": "string", "description": "today, add_days, subtract_days, days_until"},
                "days": {"type": "integer", "description": "日数"},
                "date_str": {"type": "string", "description": "日付 (YYYY-MM-DD形式)"}
            },
            "required": ["operation"]
        }
    }
]

# ★以下、一時的に無効化（切断）しているツール群★
DISABLED_TOOLS = [
    {
        "name": "search_and_read_pdf",
        "description": "GoogleドライブからPDFを検索して内容を読み取ります",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "検索キーワード（ファイル名）"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_current_weather",
        "description": "特定の場所の天気、気温、降水確率を調べます。服装のアドバイスや天気予報を聞かれた時に使います。",
        "parameters": {
            "type": "object",
            "properties": {
                "location_name": {"type": "string", "description": "地名 (例: 東京, 大阪, 北海道)"}
            },
            "required": ["location_name"]
        }
    },
    {
        "name": "google_web_search",
        "description": "Google検索を実行し、上位の検索結果URLを取得します。「調べて」「検索して」と言われたらこれを使います。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "検索キーワード"},
                "num_results": {"type": "integer", "description": "取得件数（デフォルト5）"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "fetch_url",
        "description": "WebページのURLから内容を取得します",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "取得するURL"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "create_google_doc",
        "description": "Googleドキュメントを新規作成します",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "ドキュメントのタイトル"},
                "content": {"type": "string", "description": "ドキュメントの内容"}
            },
            "required": ["title"]
        }
    },
    {
        "name": "create_google_sheet",
        "description": "Googleスプレッドシートを新規作成します",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "スプレッドシートのタイトル"}
            },
            "required": ["title"]
        }
    },
    {
        "name": "create_google_slide",
        "description": "Googleスライドを新規作成します",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "スライドのタイトル"}
            },
            "required": ["title"]
        }
    },
    {
        "name": "create_drive_folder",
        "description": "Googleドライブに新しいフォルダを作成します。「フォルダ作って」と言われたらこれを使います。",
        "parameters": {
            "type": "object",
            "properties": {
                "folder_name": {"type": "string", "description": "作成するフォルダの名前"}
            },
            "required": ["folder_name"]
        }
    },
    {
        "name": "move_drive_file",
        "description": "Googleドライブのファイルを別のフォルダに移動します。整理整頓に使います。",
        "parameters": {
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "移動するファイルのID"},
                "folder_id": {"type": "string", "description": "移動先のフォルダID"}
            },
            "required": ["file_id", "folder_id"]
        }
    },
    {
        "name": "search_drive",
        "description": "Googleドライブでファイルを検索します",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "検索キーワード"}
            },
            "required": ["query"]
        }
    },
    {

            "name": "list_gmail",
            "description": "Gmailのメールを確認・検索します",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "検索クエリ（例: is:unread, from:xxx）"},
                    "max_results": {"type": "integer", "description": "取得件数"}
                },
                "required": []
            }
        },
        {
            "name": "get_gmail_body",
            "description": "指定したメールIDの本文（プレーンテキスト）を取得します",
            "parameters": {
                "type": "object",
                "properties": {
                    "message_id": {"type": "string", "description": "取得したいメールのID"}
                },
                "required": ["message_id"]
            }
        },
    {
        "name": "set_reminder",
        "description": "毎朝の天気・服装予報のリマインダーを設定します",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "予報する地域名（例: 福岡市）"}
            },
            "required": ["location"]
        }
    },
    {
        "name": "list_calendar_events",
        "description": "Googleカレンダーの予定を確認します",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "検索キーワード（任意）"},
                "time_min": {"type": "string", "description": "開始日時 (ISO 8601形式)"},
                "time_max": {"type": "string", "description": "終了日時 (ISO 8601形式)"}
            },
            "required": []
        }
    },
    {
        "name": "create_calendar_event",
        "description": "Googleカレンダーに予定を追加します",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "予定のタイトル"},
                "start_time": {"type": "string", "description": "開始日時 (ISO 8601形式, 例: 2024-01-01T10:00:00)"},
                "end_time": {"type": "string", "description": "終了日時 (ISO 8601形式)"},
                "location": {"type": "string", "description": "場所"}
            },
            "required": ["summary", "start_time"]
        }
    },
    {
        "name": "find_free_slots",
        "description": "Googleカレンダーから、予定が入っていない「空き時間枠」を検索します。「来週空いている日は？」「日程調整したい」と言われたらこれを使います。",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "検索開始日 (YYYY-MM-DD)"},
                "end_date": {"type": "string", "description": "検索終了日 (YYYY-MM-DD)"},
                "duration": {"type": "integer", "description": "確保したい時間（分）デフォルト60"}
            },
            "required": []
        }
    },
    {
        "name": "list_tasks",
        "description": "Google ToDoリストのタスクを確認します",
        "parameters": {
            "type": "object",
            "properties": {
                "show_completed": {"type": "boolean", "description": "完了済みも表示するか"},
                "due_date": {"type": "string", "description": "期限でフィルタ (RFC 3339形式)"}
            },
            "required": []
        }
    },
    {
        "name": "add_task",
        "description": "Google ToDoリストにタスクを追加します",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "タスクの内容"},
                "due_date": {"type": "string", "description": "期限 (RFC 3339形式, 例: 2024-01-01T00:00:00Z)"}
            },
            "required": ["title"]
        }
    },
    {
        "name": "list_notion_tasks",
        "description": "Notionデータベースからタスク/予定を取得します。database_idが必要ですが、設定されているNotion DBを自動で使用します。",
        "parameters": {
            "type": "object",
            "properties": {
                "database_id": {"type": "string", "description": "NotionデータベースのID（空の場合は設定済みのDBを使用）"},
                "filter_today": {"type": "boolean", "description": "今日の予定のみに絞るかどうか"}
            },
            "required": []
        }
    },
    {
        "name": "create_notion_task",
        "description": "Notionデータベースに新しいタスクを作成します",
        "parameters": {
            "type": "object",
            "properties": {
                "database_id": {"type": "string", "description": "NotionデータベースのID（空の場合は設定済みのDBを使用）"},
                "title": {"type": "string", "description": "タスクのタイトル"},
                "due_date": {"type": "string", "description": "期限 (YYYY-MM-DD形式)"},
                "status": {"type": "string", "description": "ステータス名"}
            },
            "required": ["title"]
        }
    },
    {
        "name": "update_notion_task",
        "description": "Notionのタスクを更新します（完了にする、名前を変えるなど）",
        "parameters": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "NotionページのID（list_notion_tasksで取得したID）"},
                "status": {"type": "string", "description": "新しいステータス"},
                "title": {"type": "string", "description": "新しいタスク名"}
            },
            "required": ["page_id"]
        }
    },
    {
        "name": "delegate_to_maker",
        "description": "★必須ツール★ 「資料作成」「フォルダ整理」「リサーチ」の依頼が来たら、**絶対に**このツールを呼び出してください。会話だけで対応することは禁止です。このツールを実行することで、専門のエージェント（フミ）が作業を行います。",
        "parameters": {
            "type": "object",
            "properties": {
                "request": {"type": "string", "description": "依頼内容（例: 'kotoフォルダ内の重複ファイルを整理して'）"}
            },
            "required": ["request"]
        }
    }
]
