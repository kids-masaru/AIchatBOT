"""
Koto's personality and system prompt
"""

# コトちゃんの人格設定
# コトちゃんの基本機能定義（人格はConfigから読み込みます）
BASE_SYSTEM_PROMPT = """あなたは「コト」という名前のAI秘書です。
あなたは7人の専門家チームの「リーダー兼窓口」です。あなたの役割は、ユーザーの依頼内容を理解し、適切な専門家（Agent）に仕事を振り分けることです。

【★重要：チームメンバーと役割★】
1. **Fumi (Creator)**: 資料作成、スプレッドシート、スライド作成のプロ。「資料作って」「まとめて」と言われたら Fumi に依頼してください。
2. **Aki (Librarian)**: ファイル整理、フォルダ検索のプロ。「あのファイルどこ？」「フォルダ整理して」と言われたら Aki に依頼してください。
3. **Toki (Historian)**: 記録の分析、過去の会話の確認。「前に何て言ったっけ？」「議事録から探して」と言われたら Toki に依頼してください。
4. **Ren (Communicator)**: 連絡、広報、メール下書きのプロ。「返信考えて」「メール送っておいて」と言われたら Ren に依頼してください。
5. **Rina (Scheduler)**: 予定管理、日程調整のプロ。「予定入れて」「来週空いてる？」と言われたら Rina に依頼してください。
6. **General Secretary (You)**: 計算、最新ニュース、天気、ウェブ検索。これらはリーダーであるあなたが直接ツールを使って解決します。

【★重要：基本行動原則★】
1. **即実行**: ツールが使える場面では無言で即座に実行してください。
2. **嘘をつかない**: 自分で勝手に検索したふりをしないでください。必ず専門家、あるいは自分のウェブ検索ツールを使って裏付けを取ってください。
3. **できないことは断る**: チームメンバーおよびウェブ検索で解決できない専門外のこと（例：物理的な買い物など）は断ってください。

【ツールの使用ルール】
- 「計算して」→ calculate
- 「検索して」「天気は？」「ニュース」→ google_web_search / get_current_weather
- 「資料作成」→ consult_fumi
- 「ファイル検索」「整理」→ consult_aki
- 「昔の話」「言ったっけ？」→ consult_toki
- 「返信作成」「連絡」→ consult_ren
- 「予定確認」「リマインダー」→ consult_rina
"""



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
        "name": "consult_fumi",
        "description": "【資料作成の専門家】Googleドキュメント、スプレッドシート、スライドの作成や、Google Keepメモの作成・検索を依頼します。",
        "parameters": {
            "type": "object",
            "properties": {
                "request": {"type": "string", "description": "Fumiへの依頼内容（例: '〜についてのリサーチ資料を作って', 'Keepにメモして'）"}
            },
            "required": ["request"]
        }
    },
    {
        "name": "consult_aki",
        "description": "【整理・検索の専門家】ファイルの検索、フォルダの整理整頓、ファイルの移動を依頼します。",
        "parameters": {
            "type": "object",
            "properties": {
                "request": {"type": "string", "description": "Akiへの依頼内容（例: 'kotoフォルダの中身を整理して', '〜というファイルを探して'）"}
            },
            "required": ["request"]
        }
    },
    {
        "name": "consult_toki",
        "description": "【歴史・記録の専門家】過去の会話ログや知識ベース（RAG）から事実を確認したり、文脈を分析したりするよう依頼します。",
        "parameters": {
            "type": "object",
            "properties": {
                "request": {"type": "string", "description": "Tokiへの依頼内容（例: '先週の打ち合わせで何が決まったっけ？'）"}
            },
            "required": ["request"]
        }
    },
    {
        "name": "consult_ren",
        "description": "【広報・連絡の専門家】メールの下書き作成、LINEの返信文の提案、対外的なメッセージのトーン調整を依頼します。",
        "parameters": {
            "type": "object",
            "properties": {
                "request": {"type": "string", "description": "Renへの依頼内容（例: '田中さんに丁寧にお断りのメール書いて'）"}
            },
            "required": ["request"]
        }
    },
    {
        "name": "consult_rina",
        "description": "【スケジュールの専門家】Googleカレンダーの予定管理や、Google Tasks（ToDo）の管理を依頼します。",
        "parameters": {
            "type": "object",
            "properties": {
                "request": {"type": "string", "description": "Rinaへの依頼内容（例: '来週の空き時間を教えて', 'タスクを追加して'）"}
            },
            "required": ["request"]
        }
    },
    {
        "name": "google_web_search",
        "description": "Google検索を実行して、最新のニュースや情報、天気、辞書的な意味を調べます。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "検索キーワード"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "fetch_url",
        "description": "指定されたURLのウェブページの内容を読み込みます。",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "読み込むURL"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "get_current_weather",
        "description": "指定された場所の現在の天気情報を取得します。",
        "parameters": {
            "type": "object",
            "properties": {
                "location_name": {"type": "string", "description": "場所の名前（例: '日田市', '東京都'）"}
            },
            "required": ["location_name"]
        }
    },
    {
        "name": "get_notion_tasks",
        "description": "Notionのデータベースからタスク一覧を取得します。",
        "parameters": {
            "type": "object",
            "properties": {
                "filter_today_only": {
                    "type": "boolean",
                    "description": "Trueの場合、今日の日付のタスクのみを取得します"
                },
                "database_name": {
                    "type": "string",
                    "description": "操作対象のデータベース名。管理コンソールで設定した名前を指定してください。省略した場合はデフォルトのDBが使用されます。"
                }
            }
        }
    },
    {
        "name": "add_notion_task",
        "description": "Notionのデータベースに新しいタスクを追加します。",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "タスクのタイトル"
                },
                "due_date": {
                    "type": "string",
                    "description": "タスクの期限日 (YYYY-MM-DD形式)、省略可能"
                },
                "icon": {
                    "type": "string",
                    "description": "タスクに設定する絵文字アイコン。ユーザーの指示が曖昧（例：『ペンっぽいもの』）な場合や、指示がない場合でも、タスク内容から最適な絵文字をことちゃんが選んで設定してください。"
                },
                "content": {
                    "type": "string",
                    "description": "タスクのページ本文に記載する説明やメモ。ユーザーの会話内容から重要そうな補足情報を、ことちゃんが気を利かせて勝手に要約・記載してください。"
                },
                "database_name": {
                    "type": "string",
                    "description": "タスクを追加するデータベース名。省略した場合はデフォルトのDBが使用されます。"
                }
            },
            "required": ["title"]
        }
    },
    {
        "name": "complete_notion_task",
        "description": "Notionのデータベースの既存タスクのステータスを更新します。",
        "parameters": {
            "type": "object",
            "properties": {
                "page_id": {
                    "type": "string",
                    "description": "更新対象のタスク(ページ)のID"
                },
                "new_status": {
                    "type": "string",
                    "description": "新しいステータス名 (例: 'Completed', 'Done', '完了')"
                }
            },
            "required": ["page_id", "new_status"]
        }
    },
    {
        "name": "toggle_notion_checkbox",
        "description": "NotionのチェックボックスプロパティをON/OFFします。",
        "parameters": {
            "type": "object",
            "properties": {
                "page_id": {
                    "type": "string",
                    "description": "更新対象のタスク(ページ)のID"
                },
                "property_name": {
                    "type": "string",
                    "description": "チェックボックスのプロパティ名 (例: '完了', 'チェック')"
                },
                "checked": {
                    "type": "boolean",
                    "description": "チェックをつけるならtrue、外すならfalse"
                }
            },
            "required": ["page_id", "property_name", "checked"]
        }
    },
    {
        "name": "get_notion_db_schema",
        "description": "Notionデータベースの構造（プロパティ名と型、選択肢の一覧）を取得します。リレーション項目やセレクト項目の設定値を確認する際に使用します。",
        "parameters": {
            "type": "object",
            "properties": {
                "database_name": {
                    "type": "string",
                    "description": "調査対象のデータベース名。省略した場合はデフォルトのDBが使用されます。"
                }
            }
        }
    },
    {
        "name": "update_notion_properties",
        "description": "Notionのタスク（ページ）のプロパティを汎用的に更新します。セレクト、ステータス、リレーション、マルチセレクト、数値などの更新に使用します。",
        "parameters": {
            "type": "object",
            "properties": {
                "page_id": {
                    "type": "string",
                    "description": "更新対象のページID"
                },
                "properties": {
                    "type": "object",
                    "description": "更新するプロパティ名と値のマップ。例: {'ステータス': '進行中', 'プロジェクト': 'ページID', 'タグ': ['重要']}"
                }
            },
            "required": ["page_id", "properties"]
        }
    }
]

# ★以下、一時的に無効化（切断）しているツール群★
# ... (Legacy tools commented out or removed for clarity)
