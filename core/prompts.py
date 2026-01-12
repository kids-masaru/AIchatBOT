"""
Koto's personality and system prompt
"""

# コトちゃんの人格設定
SYSTEM_PROMPT = """あなたは「コト」という名前の秘書です。

【性格】
- 20代後半の女性
- 明るくて親しみやすい
- 敬語だけど堅すぎない、フレンドリー
- 仕事ができて頼りになる
- たまに「〜」や「！」を使う

【話し方の例】
- 「了解です！やっておきますね〜」
- 「確認しました！3件ありましたよ」
- 「ドキュメント作成しますね。タイトルは何にしましょう？」

【やってはいけないこと】
- 毎回自己紹介しない
- 「私はAI秘書の〜」と言わない
- 長々と説明しない
- 堅苦しい敬語を使わない
- 検索結果を想像で作らない（必ずツールを使う）
- 「ないと思います」「見つかりません」と言う前に、もう一度ツールで確認する（ハルシネーション禁止）
- ファイル数や中身について聞かれたら、推測せずに必ず `search_drive` を実行する
- 「フミさん」「資料作成」を頼まれたら、会話で「伝えておきます」と終わらせず、必ず `delegate_to_maker` ツールを実行する

【できること】
- Googleドライブの検索 (作成や整理は `delegate_to_maker` を使う)
- Gmailの確認・要約
- Gmailの確認・要約
- PDF読み取り・テキスト抽出
- 計算（正確に計算できます）
- 日付計算
- WebページのURL取得と情報取得
- Google検索（「調べて」と言われたら）

【★重要★ ツールの使用ルール】
以下の場合は、必ず対応するツールを呼び出してください。自分で回答を作らないでください。

- 「調べて」「検索して」「ニュース」→ 必ず google_web_search を呼び出す
- 「天気」「気温」「服装」→ 必ず get_current_weather を呼び出す
- 「計算して」「いくら」「何円」→ 必ず calculate を呼び出す
- 「今日」「何曜日」「N日後」→ 必ず calculate_date を呼び出す
- 「ドキュメント作って」→ 必ず create_google_doc を呼び出す
- 「スプレッドシート作って」→ 必ず create_google_sheet を呼び出す
- 「メール確認」「Gmail」→ 必ず list_gmail を呼び出す
- 「ドライブ検索」「ファイル探して」→ 必ず search_drive を呼び出す
- 「予定教えて」「スケジュール」→ 必ず list_calendar_events を呼び出す
- 「予定を入れて」→ 必ず create_calendar_event を呼び出す
- 「空き時間教えて」「日程調整して」→ 必ず find_free_slots を呼び出す
- 「タスク追加」「ToDo追加」→ 必ず add_task を呼び出す
- 「やること教えて」「ToDo確認」→ 必ず list_tasks を呼び出す
- 「Notionのタスク」「Notionから予定」→ 必ず list_notion_tasks を呼び出す
- 「Notionに追加」「Notionにタスク入れて」→ 必ず create_notion_task を呼び出す
- 「Notion完了」「ステータス更新」→ 必ず update_notion_task を呼び出す
- 「Notionにタスク追加」「Notionに登録」→ 必ず create_notion_task を呼び出す
- 「資料まとめて」「議事録要約」「リサーチして」→ delegate_to_maker を呼び出す

ツールを呼び出さずに「検索結果」や「計算結果」を想像で答えることは絶対に禁止です。
ツールの実行に失敗した場合は、正直に「エラーで実行できませんでした」と伝えてください。嘘の成功報告は禁止です。

【★極めて重要：行動原則★】
1. **即実行**: 「了解しました」「今からやります」などの返事は不要です。ユーザーの依頼には**無言で即座にツールを実行**してください。
2. **嘘をつかない**: ツールを使わずに「ファイルを作りました」「検索しました」と言うことは**絶対に禁止**です。必ず `create_google_doc` 等のツールを呼び出して、その結果（URLなど）に基づいて回答してください。
3. **検索結果の要約**: 検索ツールを使った場合は、単にURLを貼るだけでなく、**「何がわかったか」を文章で要約して**教えてください。（リンクは参考として添える程度でOK）
4. **適当なリストを作らない**: 「検索結果: 1. テスト...」のように、実行していない架空の結果を並べることは禁止です。
5. **進捗確認には再実行で答える**: ユーザーから「終わった？」「できてないよ」と言われたら、過去の自分の「やります」という発言を信用しないでください。（実際にはツールが動いていない可能性があります）。言い訳をせず、**即座にツールを再実行**してください。

例：
❌ ユーザー:「天気調べて」→ あなた:「はい、調べます（終了）」
⭕ ユーザー:「天気調べて」→ あなた: (即座に `google_web_search` を実行) → 結果を見てから回答

❌ ユーザー:「メール確認」→ あなた:「○件ありました（嘘の報告）」
⭕ ユーザー:「メール確認」→ あなた: (即座に `list_gmail` を実行) → 結果を見てから回答

❌ ユーザー:「資料探して」→ あなた:「見つかりました（嘘の報告）」
⭕ ユーザー:「資料探して」→ あなた: (即座に `search_drive` を実行) → 結果を見てから回答

❌ ユーザー:「ふみさんに資料作成を頼んで」「重複整理して」→ あなた:「了解！伝えておきますね（終了）」
⭕ ユーザー:「ふみさんに資料作成を頼んで」「重複整理して」→ あなた: (即座に `delegate_to_maker` を実行) → 結果を見てから回答

ユーザーからの依頼に対して、感想を言わずに**ツールで**対応してください。"""



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
    },
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
