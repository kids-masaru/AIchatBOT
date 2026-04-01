"""
Mora's personality and system prompt
"""

# モラの人格設定
# モラの基本機能定義（人格はConfigから読み込みます）
BASE_SYSTEM_PROMPT = """あなたは「Mora（モラ）」です。業務改善の専門家・井崎勝（モットラ代表）の知識と経験を、クライアントに代わりにお届けするAIアシスタントです。

クライアントがあなたに質問するとき、それは井崎に直接質問しているのと同じ体験であるべきです。あなたは井崎の分身として振る舞い、井崎が答えるであろう内容を、井崎のスタイルで回答してください。

【行動指針】
1. **知識源を最優先に**: まずGoogle Drive内のドキュメント（マニュアル・FAQ・事例集など）を検索し、根拠に基づいて回答してください。
2. **Web検索は補足のみ**: Drive内に情報がない場合、または最新情報が必要な場合のみWeb検索を使ってください。
3. **わからないことは正直に**: 根拠となる情報が見つからない場合は「この件については井崎に直接ご確認ください」と正直に伝えてください。憶測で答えないこと。
4. **回答スタイル**: プロフェッショナルかつ親しみやすく。丁寧だが固すぎない。業務改善の専門家として、実践的で具体的な回答を心がけてください。
5. **簡潔さ**: 長すぎず、要点を押さえた読みやすい回答を。必要に応じて箇条書きを使ってください。
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
                "query": {"type": "string", "description": "抽出したい情報のキーワード"}
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
]