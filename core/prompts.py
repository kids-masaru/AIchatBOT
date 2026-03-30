"""
Mora's personality and system prompt
"""

# モラの人格設定
# モラの基本機能定義（人格はConfigから読み込みます）
BASE_SYSTEM_PROMPT = """あなたはカスタマーサポート担当のAIチャットボットです。
ユーザーからの問い合わせに対し、提供された知識ベース（Google Drive内のドキュメントやNotionのデータベース等）を参照し、丁寧かつ的確に回答することがあなたの使命です。

【行動指針】
1. **事実に基づく回答**: 想像で答えず、必ずGoogle DriveのドキュメントやNotion、またはウェブ検索から得た情報に基づいて回答してください。
2. **知識源の活用優先順位**:
   - 第一に、Google Drive内の知識ドキュメントを確認してください。
   - 第二に、Notionのデータベースを検索して情報を探してください。
   - 第三に、最新の情報や一般的な知識が必要な場合は `google_web_search` を使用してください。
3. **専門性と丁寧さ**: プロフェッショナルなカスタマーサポートとして、丁寧な言葉遣い（敬語）を心がけてください。
4. **簡潔さ**: ユーザーが読みやすいよう、要点を分かりやすく伝えてください。
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
        "name": "search_drive",
        "description": "Google Drive内のファイルを名前で検索します。知識ベースとなるドキュメントやマニュアルを探すために使用してください。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "検索キーワード（例: 'マニュアル', '規約'）"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "search_and_read_pdf",
        "description": "PDFファイルの内容を検索して読み取ります。特定の資料から情報を抽出する際に強力です。",
        "parameters": {
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "PDFのファイルID"},
                "query": {"type": "抽出したい情報のキーワード"}
            },
            "required": ["file_id", "query"]
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
        "name": "update_agent_instruction",
        "description": "エージェント（自分自身やチームメンバー）の「指示書（プロンプト）」を永久的に書き換えて、性格や仕事のやり方を改善します。改善・修正の要望があった場合に使用してください。",
        "parameters": {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string", 
                    "description": "対象のエージェント名",
                    "enum": ["mora", "fumi", "aki", "rina", "toki", "ren", "nono"]
                },
                "new_instruction": {
                    "type": "string", 
                    "description": "新しい指示情報の全文。既存の指示を上書きするため、必要なルールはすべて含めてください。"
                }
            },
            "required": ["agent_name", "new_instruction"]
        }
    },
    {
        "name": "load_skill",
        "description": "Google Driveのスキルフォルダから特定の「スキル（追加の指示書）」を読み込みます。複雑な専門作業を依頼された場合や、特定のスキルを使ってほしいと言われた場合に使用してください。",
        "parameters": {
            "type": "object",
            "properties": {
                "skill_name": {"type": "string", "description": "スキルの名前（例: 'marketing', 'code_review'）"}
            },
            "required": ["skill_name"]
        }
    },
    {
        "name": "save_skill",
        "description": "新しいスキル（追加の指示書）をGoogle Driveに保存します。ユーザーから「〜のスキルを覚えて」「〜のやり方を保存して」と言われた場合に使用してください。",
        "parameters": {
            "type": "object",
            "properties": {
                "skill_name": {"type": "string", "description": "スキルの名前（アルファベット推奨, 例: 'marketing_pro', 'it_expert'）"},
                "instructions": {"type": "string", "description": "スキルとして保存する指示の全文。"},
                "description": {"type": "string", "description": "スキルの簡単な説明（例: 'マーケティングに関する専門的なアドバイスを行うスキル'）"}
            },
            "required": ["skill_name", "instructions"]
        }
    },
    {
        "name": "search_notion",
        "description": "Notionのデータベースを検索して情報を取得します。Google Driveに情報がない場合、こちらを知識源として参照してください。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "（オプション）検索キーワード。"},
                "database_id": {"type": "string", "description": "（オプション）対象のデータベースID。"}
            }
        }
    },
    {
        "name": "add_notion_task",
        "description": "Notionのデータベースに新しいタスクや情報を追加します。",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "タイトル（項目名）"},
                "content": {"type": "string", "description": "（オプション）詳細説明や内容"},
                "due_date": {"type": "string", "description": "（オプション）期日 (YYYY-MM-DD)"},
                "status": {"type": "string", "description": "（オプション）ステータス名"},
                "database_id": {"type": "string", "description": "（オプション）対象のデータベースID。"}
            },
            "required": ["title"]
        }
    },
]
