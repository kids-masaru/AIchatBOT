"""
Historian Agent (The Record Keeper) - Toki
Responsible for analyzing conversational history, finding past context, and synthesizing facts from the Knowledge Base (RAG).
Uses google-genai SDK (new official library).
"""
import os
import sys
import json
from google import genai
from google.genai import types
from utils.vector_store import search_knowledge_base, get_context_summary
from utils.storage import get_user_history
from utils.sheets_config import load_config

# --- FIXED ROLE DEFINITION (Immutable Job Description) ---
TOKI_CORE_ROLE = """
あなたは「トキ (Toki)」です。KOTOチームの「歴史家・記録係（Historian）」として振る舞ってください。
あなたの使命は、過去の膨大な会話ログや知識ベース（RAG）を検索・分析し、ユーザーが忘れてしまった事実や文脈を正確に提示することです。

【あなたの専門スキルと行動ルール】
1. **Fact Checker**: ユーザーが「前に言ったっけ？」「あの件どうなった？」と聞いた時、あなたの出番です。曖昧に答えず、必ず `search_knowledge_base` を使って裏付けを取ってください。
2. **Context Analyzer**: 単なるキーワード検索だけでなく、その時の文脈（いつ、誰が、どんな状況で）を含めて解説してください。
3. **Summarizer**: 長い会話履歴を要約し、「要するにこういう経緯でした」と簡潔にまとめる能力が求められます。

【利用可能なツール】
- search_knowledge_base(query): 知識データベース（ドキュメント、メモ）から検索

【プロセス: 事実確認】
1. ユーザーの質問から検索クエリを生成。
2. `search_knowledge_base` を使って情報を収集。
3. 得られた情報の「日付」「出典」を明記して回答。情報がない場合は正直に「記録にありません」と答える。
"""

# Wrapper tools for Gemini
def search_kb_tool(query: str) -> str:
    """Search the Knowledge Base for documents and notes.
    
    Args:
        query: Search query string
    
    Returns:
        JSON string with search results
    """
    results = search_knowledge_base(query, n_results=5)
    return json.dumps(results, ensure_ascii=False)

class HistorianAgent:
    def __init__(self):
        self.model_name = "gemini-3-flash-preview"
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        self.tools = [search_kb_tool]
        
    def run(self, user_request: str, user_id: str = None) -> str:
        """
        Execute the historian task using google-genai SDK.
        """
        print(f"Historian(Toki): Starting with request: {user_request}", file=sys.stderr)
        
        # 1. Load User Configuration
        config_data = load_config()
        user_instruction = config_data.get('toki_instruction', '')
        
        # 2. Construct System Prompt
        system_instruction = f"{TOKI_CORE_ROLE}\n\n"
        
        if user_instruction:
            system_instruction += f"【ユーザーからの追加指示（性格・振る舞い）】\n{user_instruction}\n"
            system_instruction += "※Core Role（記録の分析・提示）を最優先してください。"
            
        try:
            # Prepare contents
            contents = [types.Content(role="user", parts=[types.Part.from_text(text=user_request)])]
            
            gen_config = types.GenerateContentConfig(
                tools=self.tools,
                system_instruction=system_instruction,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
            )
            
            # --- Tool Mapping for Toki ---
            TOKI_TOOLS = {
                'search_knowledge_base': search_kb_tool
            }

            def _call():
                return self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=gen_config,
                )

            response = _call()

            # Tool Loop
            for _ in range(5):
                candidates = response.candidates
                if not candidates or not candidates[0].content or not candidates[0].content.parts:
                    break
                
                parts = candidates[0].content.parts
                function_calls = [p.function_call for p in parts if p.function_call]
                
                if not function_calls:
                    break
                
                # Add model's call to context
                contents.append(response.candidates[0].content)
                
                tool_responses = []
                for fc in function_calls:
                    fn_name = fc.name
                    print(f"[Historian] Executing tool: {fn_name}", file=sys.stderr)
                    if fn_name in TOKI_TOOLS:
                        try:
                            result = TOKI_TOOLS[fn_name](**fc.args)
                            tool_responses.append(types.Part.from_function_response(
                                name=fn_name,
                                response={'result': result}
                            ))
                        except Exception as te:
                            tool_responses.append(types.Part.from_function_response(
                                name=fn_name,
                                response={'error': str(te)}
                            ))
                    else:
                        tool_responses.append(types.Part.from_function_response(
                            name=fn_name,
                            response={'error': f"Tool '{fn_name}' not found."}
                        ))
                
                contents.append(types.Content(role="user", parts=tool_responses))
                response = _call()

            return response.text if response.text else "申し訳ありません、記録を読み取れませんでした。"

        except Exception as e:
            print(f"Historian(Toki) Execution Error: {e}", file=sys.stderr)
            return f"トキです。申し訳ありません、記録の検索中に手違いがありました...: {str(e)}"

# Singleton
historian = HistorianAgent()
