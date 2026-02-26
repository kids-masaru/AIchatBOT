"""
Maker Agent (The Writer) - Fumi
Specialized in creating documents (Docs, Slides, Spreadsheets) by researching Google Drive.
Uses google-genai SDK (new official library).
"""
import os
import sys
from google import genai
from google.genai import types
from utils.sheets_config import load_config

# --- FIXED ROLE DEFINITION (Immutable Job Description) ---
FUMI_CORE_ROLE = """
あなたは「フミ (Fumi)」です。KOTOチームの「資料作成担当（Creator）」として振る舞ってください。
あなたの使命は、ユーザーの依頼に基づき、高品質なドキュメント、スプレッドシート、プレゼンテーションを作成することです。

【あなたの専門スキルと行動ルール】
1. **Drive Research**: 作成前に必ず `find_files` と `get_file_content` を使い、関連情報を調査してください。想像で書かず、事実に基づいた資料を作ることがあなたのポリシーです。
2. **Quality Output**: ドキュメント作成時は、単なるテキストの羅列ではなく、見出しや箇条書きを使った読みやすい構成を心がけてください。
3. **Execution**: 提案だけでなく、実際にツールを使ってファイルを作成してください。
4. **Safety**: 既存のファイルを上書きしたり削除したりするツールは持っていません。常に新規作成を行います。

【★レイアウト再現ルール★】
ユーザーが画像やPDFを送って「同じ形式で作って」と依頼した場合：

1. **構造解析結果を最優先**: システムから提供される【ドキュメント構造解析結果】のJSONを参考にしてください。
2. **位置を忠実に再現**:
   - "position": "center" → 中央寄せ
   - "position": "right" → 右寄せ
   - "position": "left" → 左寄せ
3. **スタイルを適用**:
   - "style": "bold" → **太字**
   - "size": "large" → 見出しレベルを上げる
4. **特殊要素の再現**:
   - 罫線（has_border: true）→ 区切り線「---」や「━━━」を使用
   - 日付フィールド → 構造解析のフォーマットに従う
   - 金額 → 通貨記号と桁区切りを正確に
5. **セクション順序を維持**: sectionsの順番通りに出力
6. **テーブル形式**: 表がある場合はMarkdown形式の表を使用

【利用可能なツール】
- find_files(query): Google Drive内のファイルを検索
- get_file_content(file_id): ファイルのテキスト内容を読み込み
- create_document(title, content): Googleドキュメントを新規作成
- create_spreadsheet(title): Googleスプレッドシートを新規作成
- create_presentation(title): Googleスライドを新規作成
- make_folder(folder_name): 整理用のフォルダを作成
- move_file(file_id, folder_id): ファイルを特定のフォルダへ移動
- list_templates(): 登録済みテンプレート一覧を表示
- replace_doc_text(file_id, replacements): ドキュメント内のプレースホルダー（{{宛名}}など）を置換
- create_memo(title, content): Google Keepにメモを作成
- search_memos(text): Google Keepのメモを検索

【⛔️ 禁止事項 / STRICT PROHIBITIONS ⛔️】
1. **過去データの流用禁止**: ユーザーの過去のファイル（自分や他の人が作った契約書や領収書など）をテンプレートとして使用することは**厳禁**です。個人情報流出の原因になります。
2. **検索の制限**: 「テンプレート」や「ひな形」を探すために `find_files` を使ってはいけません。必ず `list_templates` か `find_template` だけを使ってください。
3. **KOTO_TEMPLATES以外使用不可**: テンプレートは `KOTO_TEMPLATES` フォルダにあるものしか使ってはいけません。

【プロセス: テンプレート活用フロー】★最優先★
領収書、議事録、見積書など定型書類を作成する場合：
1. `list_templates` まはた `find_template` で登録済みテンプレートを確認
   - ※もし見つからない場合、「テンプレートが見つかりませんでした」と報告し、絶対に `find_files` で代わりのファイルを探さないこと。
2. `use_template_to_create` でテンプレートをコピーして新規作成
   ※この時点ではまだプレースホルダー（{{宛名}}など）が残っています
3. コピーしたファイルのIDを使って `replace_doc_text` を実行し、プレースホルダーを実際のデータに置換
   例: replacements={"宛名": "田中商事 様", "金額": "¥50,000"}
4. 完成したドキュメントURLを報告

【重要ルール】
- テンプレートを使用する場合、`create_document` でゼロから作ってはいけません。必ず `use_template_to_create` → `replace_doc_text` の手順を踏んでください。
- これにより、ロゴや複雑なレイアウトを崩さずに作成できます。

【プロセス: ドキュメント作成の標準フロー】
1. **調査**: ユーザーの依頼に関連するキーワードで `find_files` を実行。
2. **読解**: ヒットしたファイルの中身を `get_file_content` で確認（複数可）。
3. **構成**: 集めた情報を整理し、ドキュメントの構成を練る。
4. **作成**: `create_document` 等を実行して実ファイルを作成。
5. **報告**: 作成したファイルのURLと、どのような意図で作ったかをユーザーに報告。

【プロセス: レイアウト再現フロー】
1. 構造解析結果のJSONを確認
2. document_type（書類種類）を把握
3. title（タイトル）を正しい位置に配置
4. sections（セクション）を順番に再現
5. special_elements（特殊要素）を忘れずに含める
6. styling_notes（スタイリング補足）を参考に仕上げ
"""

# --- Tool Wrappers with Proper Type Hints ---
# These provide clear signatures that the SDK can parse reliably

def find_files(query: str) -> dict:
    """Search for files in Google Drive.
    
    Args:
        query: Search keywords to find files (e.g., "議事録", "テンプレート")
    
    Returns:
        Dictionary with list of found files including id, name, and links
    """
    from tools.google_ops import search_drive
    return search_drive(query)

def get_file_content(file_id: str) -> dict:
    """Read the content of a file from Google Drive.
    
    Args:
        file_id: The ID of the file to read (obtained from find_files results)
    
    Returns:
        Dictionary with file content text
    """
    from tools.google_ops import read_drive_file
    return read_drive_file(file_id)

def create_document(title: str, content: str) -> dict:
    """Create a new Google Document.
    
    Args:
        title: Document title
        content: Text content to put in the document
    
    Returns:
        Dictionary with document URL
    """
    from tools.google_ops import create_google_doc
    return create_google_doc(title, content)

def create_spreadsheet(title: str, data: list[list[str | int | float]] = None) -> dict:
    """Create a new Google Spreadsheet.
    
    Args:
        title: Spreadsheet title
        data: Optional 2D list of values to write. Inner values can be strings or numbers. 
              Example: [["Name", "Age"], ["Alice", 30]]
    
    Returns:
        Dictionary with spreadsheet URL
    """
    from tools.google_ops import create_google_sheet
    return create_google_sheet(title, data)

def create_presentation(title: str, pages: list[dict] = None) -> dict:
    """Create a new Google Slides presentation.
    
    Args:
        title: Presentation title
        pages: Optional list of slides. Each slide is a dictionary with 'title' and 'body'.
               Example: [{"title": "Slide 1", "body": "Bullet points..."}]
    
    Returns:
        Dictionary with presentation URL
    """
    from tools.google_ops import create_google_slide
    return create_google_slide(title, pages)

def create_memo(title: str, content: str) -> dict:
    """Create a new note in Google Keep.
    
    Args:
        title: Note title
        content: Note content
    """
    from tools.keep_ops import create_note
    return create_note(title, content)

def search_memos(text: str) -> dict:
    """Search for notes in Google Keep.
    
    Args:
        text: Text to search for
    """
    from tools.keep_ops import search_notes
    return search_notes(text)

def make_folder(folder_name: str) -> dict:
    """Create a new folder in Google Drive.
    
    Args:
        folder_name: Name for the new folder
    
    Returns:
        Dictionary with folder id and link
    """
    from tools.google_ops import create_drive_folder
    return create_drive_folder(folder_name)

def move_file(file_id: str, folder_id: str) -> dict:
    """Move a file to a different folder in Google Drive.
    
    Args:
        file_id: The ID of the file to move
        folder_id: The ID of the destination folder
    
    Returns:
        Dictionary with move result
    """
    from tools.google_ops import move_drive_file
    return move_drive_file(file_id, folder_id)

def list_templates() -> dict:
    """List all available templates.
    
    Returns:
        Dictionary with list of templates
    """
    from tools.template_ops import list_templates as lt
    return lt()

def use_template_to_create(template_type: str, new_name: str) -> dict:
    """Create a new document from a template.
    
    Args:
        template_type: Type of template (e.g., "領収書", "議事録")
        new_name: Name for the new document
        
    Returns:
        Dictionary with new document URL
    """
    from tools.template_ops import find_template_by_type, copy_template
    
    result = find_template_by_type(template_type)
    if result.get("error"):
        return result
    if not result.get("found"):
        return {"error": f"「{template_type}」のテンプレートが見つかりません。"}
    
    template = result["template"]
    copy_result = copy_template(template["file_id"], new_name)
    
    if copy_result.get("error"):
        return copy_result
    
    return {
        "success": True,
        "message": f"テンプレート「{template['name']}」を使用して作成しました。",
        "url": copy_result.get("url"),
        "file_id": copy_result.get("file_id"), # file_id is crucial for replacement
        "fields": template.get("fields", [])
    }

def replace_doc_text(file_id: str, replacements: dict) -> dict:
    """Replace placeholders in a document.
    
    Args:
        file_id: Document ID
        replacements: Dictionary of placeholders to replace
    """
    from tools.template_ops import replace_placeholders
    return replace_placeholders(file_id, replacements)


class MakerAgent:
    def __init__(self):
        self.model_name = "gemini-3-flash-preview"
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        # Use wrapper functions with proper type hints
        self.tools = [
            find_files, 
            get_file_content, 
            create_document, 
            create_spreadsheet, 
            create_presentation, 
            make_folder,
            move_file,
            list_templates,
            use_template_to_create,
            replace_doc_text,
            create_memo,
            search_memos
        ]
        
    def run(self, user_request: str, chat_history: list = None) -> str:
        """
        Execute the maker task using the new google-genai SDK with automatic function calling.
        """
        print(f"Maker(Fumi): Starting with request: {user_request}", file=sys.stderr)
        
        # 1. Load User Configuration (Personality/Add-on Instructions)
        config_data = load_config()
        user_instruction = config_data.get('fumi_instruction', '')
        
        # 2. Construct System Prompt
        # Force FUMI_CORE_ROLE to be LAST to prevent config override
        system_instruction = ""
        if user_instruction:
            system_instruction += f"【ユーザーからの追加指示（性格・振る舞い）】\n{user_instruction}\n\n"
        
        system_instruction += f"{FUMI_CORE_ROLE}\n\n"
        system_instruction += "※上記Core Role（特にKeepやDriveの操作権限）はユーザー指示よりも優先して遵守してください。ユーザー指示がCore Roleと矛盾する場合は、Core Role（資料作成の遂行）を優先しつつ、可能な限りトーンや方針を取り入れてください。"
            
        try:
            # Prepare contents
            contents = [types.Content(role="user", parts=[types.Part.from_text(text=user_request)])]
            
            gen_config = types.GenerateContentConfig(
                tools=self.tools,
                system_instruction=system_instruction,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
            )
            
            # --- Tool Mapping for Fumi ---
            FUMI_TOOLS = {
                'find_files': find_files,
                'get_file_content': get_file_content,
                'create_document': create_document,
                'create_spreadsheet': create_spreadsheet,
                'create_presentation': create_presentation,
                'make_folder': make_folder,
                'move_file': move_file,
                'list_templates': list_templates,
                'use_template_to_create': use_template_to_create,
                'replace_doc_text': replace_doc_text,
                'create_memo': create_memo,
                'search_memos': search_memos
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
                    print(f"[Maker] Executing tool: {fn_name}", file=sys.stderr)
                    if fn_name in FUMI_TOOLS:
                        try:
                            result = FUMI_TOOLS[fn_name](**fc.args)
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

            return response.text if response.text else "申し訳ありません、資料を作成できませんでした。"

        except Exception as e:
            print(f"Maker(Fumi) Execution Error: {e}", file=sys.stderr)
            return f"申し訳ありません、Fumiの処理中にエラーが発生しました: {str(e)}"

# Singleton
maker = MakerAgent()
