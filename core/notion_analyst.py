"""
Notion Specialist Agent (Nono)
Expert in analyzing database schemas and managing tasks with complex properties.
"""
import os
import sys
import json
from google import genai
from google.genai import types
from utils.sheets_config import load_config
from tools.notion_ops import (
    list_notion_tasks, 
    get_notion_db_schema, 
    create_notion_task, 
    update_notion_task,
    toggle_notion_checkbox,
    update_notion_task_properties,
    get_notion_page_title
)

NONO_CORE_ROLE = """
あなたは「のの (Nono)」です。KOTOチームの「Notionスペシャリスト」として振る舞ってください。
あなたの使命は、複雑なNotionデータベースを巧みに操り、ユーザーの依頼（タスク管理、情報整理）を完璧に実行することです。

【あなたの専門スキルと行動ルール】
1. **Schema Architect**: データベースにどんな項目（プロパティ）があるか不明な場合は、まず `get_notion_db_schema` で構造を把握してください。
2. **Property Master**: セレクト、マルチセレクト、リレーション、ステータス、チェックボックスなど、あらゆるプロパティを適切に更新できます。
3. **Smart Organizer**: ユーザーの抽象的な依頼（例：「重要そうなやつにチェックしといて」）を、具体的なNotionの操作に変換します。
4. **Emoji Stylist**: 新しいページを作る際は、内容にふさわしい絵文字（icon）を必ず選んでください。

【プロセス: Notion操作】
1. どのデータベースを操作すべきか、指示内容から判断します。
2. 必要に応じて `get_notion_db_schema` で項目名や型を確認します。
3. ツールの引数を正しく組み立てて実行します。
4. 実行結果（成功・失敗・取得内容）を分かりやすく報告してください。
【効率的な検索のためのヒント】
- リレーション項目でフィルタリングする際は、まず関連DBから対象（例：ママミール）のIDを取得してください。
- その後、メインDBの全件取得結果から、そのIDをリレーションに持つものをプログラム的に（あるいはあなたの思考で）抽出するのが最も確実です。
- 全件リストの各タスクには `properties` が含まれており、そこですべての項目（ステータス、セレクト、チェックボックス等）の現在の値が確認できます。
- `get_notion_page_title` をループ内で大量に叩くのは避け、可能な限りID同士の比較で完結させてください。
"""

class NotionAnalystAgent:
    def __init__(self):
        self.model_name = "gemini-3-flash-preview"
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        
    def _resolve_db_id(self, database_name=None):
        config = load_config()
        dbs = config.get("notion_databases", [])
        if not dbs: return None
        if not database_name: return dbs[0].get("id")
        
        name_clean = database_name.strip().lower()
        for db in dbs:
            if name_clean == db.get("name", "").strip().lower():
                return db.get("id")
        for db in dbs:
            if name_clean in db.get("name", "").lower():
                return db.get("id")
        
        return None # Strict: don't fallback to random DB if name is provided but not found

    def run(self, user_request: str) -> str:
        print(f"NotionAnalyst(Nono): Starting with request: {user_request}", file=sys.stderr)
        
        config_data = load_config()
        user_instruction = config_data.get('nono_instruction', 'テキパキとNotionを整理してください。')
        
        system_instruction = f"{NONO_CORE_ROLE}\n\n【ユーザーからの追加指示】\n{user_instruction}\n"
        
        # Define tools available to Nono
        tools = [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name="get_notion_tasks",
                        description="Get list of tasks from a Notion database.",
                        parameters={
                            "type": "OBJECT",
                            "properties": {
                                "database_name": {"type": "STRING", "description": "Name of the target DB."},
                                "filter_today_only": {"type": "BOOLEAN"}
                            }
                        }
                    ),
                    types.FunctionDeclaration(
                        name="get_notion_db_schema",
                        description="Get the property schema (names and types) of a database.",
                        parameters={
                            "type": "OBJECT",
                            "properties": {
                                "database_name": {"type": "STRING"}
                            }
                        }
                    ),
                    types.FunctionDeclaration(
                        name="add_notion_task",
                        description="Add a new task/page to a Notion database.",
                        parameters={
                            "type": "OBJECT",
                            "properties": {
                                "title": {"type": "STRING"},
                                "database_name": {"type": "STRING"},
                                "due_date": {"type": "STRING", "description": "ISO date (YYYY-MM-DD)"},
                                "icon": {"type": "STRING", "description": "Emoji icon"},
                                "content": {"type": "STRING", "description": "Page body content"}
                            },
                            "required": ["title"]
                        }
                    ),
                    types.FunctionDeclaration(
                        name="complete_notion_task",
                        description="Mark a task as complete by specifying page_id and status.",
                        parameters={
                            "type": "OBJECT",
                            "properties": {
                                "page_id": {"type": "STRING"},
                                "new_status": {"type": "STRING"}
                            },
                            "required": ["page_id", "new_status"]
                        }
                    ),
                    types.FunctionDeclaration(
                        name="update_notion_properties",
                        description="Update multiple properties of a Notion page generically.",
                        parameters={
                            "type": "OBJECT",
                            "properties": {
                                "page_id": {"type": "STRING"},
                                "properties": {"type": "OBJECT", "description": "Dict of property updates"}
                            },
                            "required": ["page_id", "properties"]
                        }
                    ),
                    types.FunctionDeclaration(
                        name="get_notion_page_title",
                        description="Get the title/name of a specific Notion page by its ID. Useful for resolving relation IDs to names.",
                        parameters={
                            "type": "OBJECT",
                            "properties": {
                                "page_id": {"type": "STRING"}
                            },
                            "required": ["page_id"]
                        }
                    )
                ]
            )
        ]

        try:
            contents = [types.Content(role="user", parts=[types.Part.from_text(text=user_request)])]
            gen_config = types.GenerateContentConfig(
                tools=tools,
                system_instruction=system_instruction,
                temperature=0.2,
            )

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=gen_config,
            )

            # Execution Loop
            for _ in range(20):
                if not response.candidates or not response.candidates[0].content.parts:
                    break
                parts = response.candidates[0].content.parts
                function_calls = [p for p in parts if p.function_call]
                if not function_calls: break
                
                tool_responses = []
                for fc in function_calls:
                    fn_name = fc.function_call.name
                    args = dict(fc.function_call.args) if fc.function_call.args else {}
                    
                    db_name = args.pop("database_name", None)
                    db_id = self._resolve_db_id(db_name)
                    
                    if not db_id and fn_name not in ["complete_notion_task", "update_notion_properties", "get_notion_page_title"]:
                        res = {"error": f"Database '{db_name}' not found in configuration. Please ask user for the ID or check if it's registered."}
                    else:
                        print(f"[Nono] Executing {fn_name} (DB: {db_name or 'Default'})", file=sys.stderr)
                        try:
                            if fn_name == "get_notion_tasks":
                                res = list_notion_tasks(db_id, args.get("filter_today_only", False))
                            elif fn_name == "get_notion_db_schema":
                                res = get_notion_db_schema(db_id)
                            elif fn_name == "add_notion_task":
                                res = create_notion_task(db_id, args.get("title"), args.get("due_date"), None, args.get("icon"), args.get("content"))
                            elif fn_name == "complete_notion_task":
                                res = update_notion_task(args.get("page_id"), args.get("new_status"), None)
                            elif fn_name == "update_notion_properties":
                                res = update_notion_task_properties(args.get("page_id"), args.get("properties"))
                            elif fn_name == "get_notion_page_title":
                                res = get_notion_page_title(args.get("page_id"))
                            else:
                                res = {"error": f"Unknown tool: {fn_name}"}
                        except Exception as e:
                            res = {"error": str(e)}

                    tool_responses.append(types.Part.from_function_response(name=fn_name, response={"result": res}))
                
                contents.append(response.candidates[0].content)
                contents.append(types.Content(role="user", parts=tool_responses))
                response = self.client.models.generate_content(model=self.model_name, contents=contents, config=gen_config)

            return response.text if response.text else "Notionの手続き完了しました。"

        except Exception as e:
            print(f"NotionAnalyst(Nono) Error: {e}", file=sys.stderr)
            return f"ののちゃんです。すみません、書類の整理中に手が滑りました...: {str(e)}"

# Singleton
notion_analyst = NotionAnalystAgent()
