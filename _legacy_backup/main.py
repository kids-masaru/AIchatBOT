from flask import Flask, request, Response
import json
import os
import sys
import hashlib
import hmac
import base64
import urllib.request
import re
import math
import tempfile
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from collections import defaultdict

# PDF library
try:
    import fitz  # PyMuPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("PyMuPDF not available", file=sys.stderr)

app = Flask(__name__)

# LINE credentials
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET', '')
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', '')

# Gemini API
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

# Google Workspace
GOOGLE_SERVICE_ACCOUNT_KEY = os.environ.get('GOOGLE_SERVICE_ACCOUNT_KEY', '{}')
GOOGLE_DELEGATED_USER = os.environ.get('GOOGLE_DELEGATED_USER', '')

# Conversation history storage (in-memory, per user)
conversation_history = defaultdict(list)
MAX_HISTORY = 50  # 50件に変更

# Temporary storage for PDFs sent by users
user_pdf_cache = {}

# Mora's personality
SYSTEM_PROMPT = """あなたは「モラ」という名前の秘書です。

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

【できること】
- Googleドキュメント/スプレッドシート/スライドの作成
- Googleドライブの検索
- Gmailの確認・要約
- PDF読み取り・テキスト抽出
- 計算（正確に計算できます）
- 日付計算
- Webページの情報取得

【重要】
- ユーザーとの過去の会話を覚えています
- 「それ」「あれ」「いいですよ」などの指示語は、直前の会話から文脈を理解して対応
- わからない場合だけ確認する
- 計算はcalculate関数を使う（正確）
- PDF読み取りはread_pdf関数を使う（高速）

ユーザーからの依頼に対して、てきぱきと対応してください。"""

# Google API scopes
SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/presentations',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/forms',
]

def get_google_credentials():
    """Get Google credentials with domain-wide delegation"""
    try:
        service_account_info = json.loads(GOOGLE_SERVICE_ACCOUNT_KEY)
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=SCOPES
        )
        if GOOGLE_DELEGATED_USER:
            credentials = credentials.with_subject(GOOGLE_DELEGATED_USER)
        return credentials
    except Exception as e:
        print(f"Credentials error: {e}", file=sys.stderr)
        return None

# ============ Python-based Tools (Fast & Accurate) ============

def calculate(expression):
    """
    Safe calculator - evaluates mathematical expressions
    Supports: +, -, *, /, **, sqrt, sin, cos, tan, log, etc.
    """
    try:
        # Clean and validate expression
        expr = expression.strip()
        
        # Replace common notation
        expr = expr.replace('×', '*').replace('÷', '/').replace('^', '**')
        expr = expr.replace('√', 'sqrt')
        
        # Allowed functions and constants
        safe_dict = {
            'sqrt': math.sqrt,
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'log': math.log,
            'log10': math.log10,
            'abs': abs,
            'round': round,
            'pi': math.pi,
            'e': math.e,
            'pow': pow,
        }
        
        # Validate - only allow safe characters
        if not re.match(r'^[\d\s\+\-\*\/\.\(\)\,a-z\_]+$', expr.lower()):
            return {"error": f"無効な文字が含まれています: {expr}"}
        
        result = eval(expr, {"__builtins__": {}}, safe_dict)
        
        # Format result
        if isinstance(result, float):
            if result.is_integer():
                result = int(result)
            else:
                result = round(result, 10)
        
        return {"success": True, "expression": expression, "result": result}
    except Exception as e:
        return {"error": f"計算エラー: {str(e)}"}

def calculate_date(operation, days=0, date_str=None):
    """
    Date calculator
    Operations: today, add_days, subtract_days, weekday, days_until
    """
    try:
        if date_str:
            base_date = datetime.strptime(date_str, '%Y-%m-%d')
        else:
            base_date = datetime.now()
        
        if operation == 'today':
            result = datetime.now()
            weekday_names = ['月', '火', '水', '木', '金', '土', '日']
            return {
                "success": True,
                "date": result.strftime('%Y年%m月%d日'),
                "weekday": weekday_names[result.weekday()] + '曜日',
                "time": result.strftime('%H:%M')
            }
        elif operation == 'add_days':
            result = base_date + timedelta(days=days)
            weekday_names = ['月', '火', '水', '木', '金', '土', '日']
            return {
                "success": True,
                "date": result.strftime('%Y年%m月%d日'),
                "weekday": weekday_names[result.weekday()] + '曜日'
            }
        elif operation == 'subtract_days':
            result = base_date - timedelta(days=days)
            weekday_names = ['月', '火', '水', '木', '金', '土', '日']
            return {
                "success": True,
                "date": result.strftime('%Y年%m月%d日'),
                "weekday": weekday_names[result.weekday()] + '曜日'
            }
        elif operation == 'days_until':
            target = datetime.strptime(date_str, '%Y-%m-%d')
            diff = (target - datetime.now()).days
            return {"success": True, "days": diff, "target": date_str}
        else:
            return {"error": f"Unknown operation: {operation}"}
    except Exception as e:
        return {"error": f"日付計算エラー: {str(e)}"}

def read_pdf_from_drive(file_id):
    """Download and read PDF from Google Drive"""
    try:
        if not PDF_AVAILABLE:
            return {"error": "PDF読み取り機能が利用できません"}
        
        creds = get_google_credentials()
        if not creds:
            return {"error": "Google認証エラー"}
        
        drive_service = build('drive', 'v3', credentials=creds)
        
        # Download file
        request = drive_service.files().get_media(fileId=file_id)
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(request.execute())
            tmp_path = tmp.name
        
        # Read PDF
        doc = fitz.open(tmp_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        
        # Cleanup
        os.unlink(tmp_path)
        
        # Truncate if too long
        if len(text) > 10000:
            text = text[:10000] + "\n...(以下省略)"
        
        return {"success": True, "text": text, "pages": len(doc)}
    except Exception as e:
        print(f"PDF error: {e}", file=sys.stderr)
        return {"error": f"PDF読み取りエラー: {str(e)}"}

def search_and_read_pdf(query):
    """Search Drive for PDF and read it"""
    try:
        creds = get_google_credentials()
        if not creds:
            return {"error": "Google認証エラー"}
        
        drive_service = build('drive', 'v3', credentials=creds)
        
        # Search for PDF
        results = drive_service.files().list(
            q=f"name contains '{query}' and mimeType='application/pdf' and trashed=false",
            pageSize=1,
            fields="files(id, name)"
        ).execute()
        
        files = results.get('files', [])
        if not files:
            return {"error": f"'{query}'に該当するPDFが見つかりませんでした"}
        
        file_info = files[0]
        pdf_result = read_pdf_from_drive(file_info['id'])
        
        if pdf_result.get('success'):
            pdf_result['filename'] = file_info['name']
        
        return pdf_result
    except Exception as e:
        return {"error": str(e)}

def fetch_url(url):
    """Fetch content from URL"""
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=10) as res:
            content = res.read().decode('utf-8', errors='ignore')
            
            # Simple HTML to text (remove tags)
            content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
            content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
            content = re.sub(r'<[^>]+>', ' ', content)
            content = re.sub(r'\s+', ' ', content).strip()
            
            if len(content) > 5000:
                content = content[:5000] + "..."
            
            return {"success": True, "content": content, "url": url}
    except Exception as e:
        return {"error": f"URL取得エラー: {str(e)}"}

# ============ Google Workspace Tools ============

def create_google_doc(title, content=""):
    """Create a Google Doc"""
    try:
        creds = get_google_credentials()
        if not creds:
            return {"error": "認証エラー"}
        
        docs_service = build('docs', 'v1', credentials=creds)
        
        doc = docs_service.documents().create(body={'title': title}).execute()
        doc_id = doc.get('documentId')
        
        if content:
            requests = [{'insertText': {'location': {'index': 1}, 'text': content}}]
            docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
        
        url = f"https://docs.google.com/document/d/{doc_id}/edit"
        return {"success": True, "title": title, "url": url, "id": doc_id}
    except Exception as e:
        print(f"Docs error: {e}", file=sys.stderr)
        return {"error": str(e)}

def create_google_sheet(title, data=None):
    """Create a Google Sheet"""
    try:
        creds = get_google_credentials()
        if not creds:
            return {"error": "認証エラー"}
        
        sheets_service = build('sheets', 'v4', credentials=creds)
        
        spreadsheet = {'properties': {'title': title}}
        result = sheets_service.spreadsheets().create(body=spreadsheet).execute()
        sheet_id = result.get('spreadsheetId')
        
        if data:
            sheets_service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range='A1',
                valueInputOption='RAW',
                body={'values': data}
            ).execute()
        
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
        return {"success": True, "title": title, "url": url, "id": sheet_id}
    except Exception as e:
        return {"error": str(e)}

def create_google_slide(title):
    """Create a Google Slides presentation"""
    try:
        creds = get_google_credentials()
        if not creds:
            return {"error": "認証エラー"}
        
        slides_service = build('slides', 'v1', credentials=creds)
        
        presentation = {'title': title}
        result = slides_service.presentations().create(body=presentation).execute()
        pres_id = result.get('presentationId')
        
        url = f"https://docs.google.com/presentation/d/{pres_id}/edit"
        return {"success": True, "title": title, "url": url, "id": pres_id}
    except Exception as e:
        return {"error": str(e)}

def search_drive(query):
    """Search Google Drive"""
    try:
        creds = get_google_credentials()
        if not creds:
            return {"error": "認証エラー"}
        
        drive_service = build('drive', 'v3', credentials=creds)
        
        results = drive_service.files().list(
            q=f"name contains '{query}' and trashed=false",
            pageSize=10,
            fields="files(id, name, mimeType, webViewLink, modifiedTime)"
        ).execute()
        
        files = results.get('files', [])
        return {"success": True, "files": files, "count": len(files)}
    except Exception as e:
        return {"error": str(e)}

def list_gmail(query="is:unread", max_results=5):
    """List Gmail messages"""
    try:
        creds = get_google_credentials()
        if not creds:
            return {"error": "認証エラー"}
        
        gmail_service = build('gmail', 'v1', credentials=creds)
        
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return {"success": True, "emails": [], "count": 0}
        
        email_list = []
        
        for msg in messages[:max_results]:
            try:
                msg_data = gmail_service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['Subject', 'From', 'Date']
                ).execute()
                
                headers = {h['name']: h['value'] for h in msg_data.get('payload', {}).get('headers', [])}
                email_list.append({
                    'id': msg['id'],
                    'subject': headers.get('Subject', '(件名なし)'),
                    'from': headers.get('From', ''),
                    'date': headers.get('Date', '')
                })
            except Exception as e:
                print(f"Error getting message: {e}", file=sys.stderr)
                continue
        
        return {"success": True, "emails": email_list, "count": len(email_list)}
    except Exception as e:
        print(f"Gmail error: {e}", file=sys.stderr)
        return {"error": f"Gmailエラー: {str(e)}"}

# ============ Tool Definitions for Gemini ============

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
    }
]

def execute_tool(tool_name, args):
    """Execute a tool and return result"""
    print(f"Executing: {tool_name}({args})", file=sys.stderr)
    
    if tool_name == "calculate":
        return calculate(args.get("expression", ""))
    elif tool_name == "calculate_date":
        return calculate_date(
            args.get("operation", "today"),
            args.get("days", 0),
            args.get("date_str")
        )
    elif tool_name == "search_and_read_pdf":
        return search_and_read_pdf(args.get("query", ""))
    elif tool_name == "fetch_url":
        return fetch_url(args.get("url", ""))
    elif tool_name == "create_google_doc":
        return create_google_doc(args.get("title", "新規ドキュメント"), args.get("content", ""))
    elif tool_name == "create_google_sheet":
        return create_google_sheet(args.get("title", "新規スプレッドシート"))
    elif tool_name == "create_google_slide":
        return create_google_slide(args.get("title", "新規スライド"))
    elif tool_name == "search_drive":
        return search_drive(args.get("query", ""))
    elif tool_name == "list_gmail":
        return list_gmail(args.get("query", "is:unread"), args.get("max_results", 5))
    else:
        return {"error": f"Unknown tool: {tool_name}"}

def format_tool_result(tool_name, result):
    """Format tool result for user response"""
    if result.get("error"):
        return f"ごめんなさい、エラーが出ちゃいました...😢\n{result['error']}"
    
    if tool_name == "calculate":
        return f"計算しました！✨\n\n{result['expression']} = **{result['result']}**"
    
    elif tool_name == "calculate_date":
        if 'time' in result:
            return f"今日は {result['date']}（{result['weekday']}）\n現在時刻: {result['time']}"
        elif 'days' in result:
            return f"{result['target']}まで **{result['days']}日** です！"
        else:
            return f"{result['date']}（{result['weekday']}）です！"
    
    elif tool_name == "search_and_read_pdf":
        text = result.get('text', '')[:1000]
        return f"PDF読み取りました！📄\n\nファイル: {result.get('filename', '')}\n\n---\n{text}"
    
    elif tool_name == "fetch_url":
        content = result.get('content', '')[:500]
        return f"Webページの内容を取得しました！🌐\n\n{content}..."
    
    elif tool_name in ["create_google_doc", "create_google_sheet", "create_google_slide"]:
        return f"作成しました！✨\n\n📄 {result.get('title', '')}\n🔗 {result['url']}"
    
    elif tool_name == "search_drive":
        files = result.get("files", [])
        if not files:
            return "検索しましたが、該当するファイルは見つかりませんでした〜"
        response = f"ドライブを検索しました！{len(files)}件見つかりましたよ✨\n\n"
        for f in files[:5]:
            response += f"📁 {f['name']}\n   {f.get('webViewLink', '')}\n\n"
        return response.strip()
    
    elif tool_name == "list_gmail":
        emails = result.get("emails", [])
        if not emails:
            return "メールは見つかりませんでした〜"
        response = f"メールを確認しました！{len(emails)}件ありますよ📧\n\n"
        for e in emails[:5]:
            from_addr = e['from'][:30] + '...' if len(e['from']) > 30 else e['from']
            response += f"📩 {e['subject']}\n   From: {from_addr}\n\n"
        return response.strip()
    
    return json.dumps(result, ensure_ascii=False)

def get_gemini_response(user_id, user_message):
    """Get response from Gemini API with function calling and conversation history"""
    if not GEMINI_API_KEY:
        return "APIキーが設定されていません〜"
    
    # Add user message to history
    conversation_history[user_id].append({"role": "user", "text": user_message})
    
    # Keep only last N messages
    if len(conversation_history[user_id]) > MAX_HISTORY:
        conversation_history[user_id] = conversation_history[user_id][-MAX_HISTORY:]
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    
    headers = {'Content-Type': 'application/json'}
    
    # Build conversation contents
    contents = []
    contents.append({"role": "user", "parts": [{"text": SYSTEM_PROMPT}]})
    contents.append({"role": "model", "parts": [{"text": "了解しました！"}]})
    
    for msg in conversation_history[user_id]:
        contents.append({
            "role": msg["role"] if msg["role"] == "model" else "user",
            "parts": [{"text": msg["text"]}]
        })
    
    data = {
        "contents": contents,
        "tools": [{"function_declarations": TOOLS}],
        "generationConfig": {"temperature": 0.8, "maxOutputTokens": 1024}
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers=headers,
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            result = json.loads(res.read().decode('utf-8'))
            candidates = result.get('candidates', [])
            
            if not candidates:
                return 'ちょっと調子悪いみたいです...もう一度試してもらえますか？'
            
            content = candidates[0].get('content', {})
            parts = content.get('parts', [])
            
            for part in parts:
                if 'functionCall' in part:
                    func_call = part['functionCall']
                    tool_name = func_call.get('name')
                    tool_args = func_call.get('args', {})
                    
                    tool_result = execute_tool(tool_name, tool_args)
                    response_text = format_tool_result(tool_name, tool_result)
                    
                    conversation_history[user_id].append({"role": "model", "text": response_text})
                    return response_text
                
                if 'text' in part:
                    response_text = part['text']
                    conversation_history[user_id].append({"role": "model", "text": response_text})
                    return response_text
            
            return 'ちょっとわからなかったです...もう少し詳しく教えてもらえますか？'
    
    except Exception as e:
        print(f"Gemini error: {e}", file=sys.stderr)
        return "ちょっとエラーが出ちゃいました...😢"

def verify_signature(body, signature):
    if not LINE_CHANNEL_SECRET:
        return True
    hash = hmac.new(LINE_CHANNEL_SECRET.encode('utf-8'), body.encode('utf-8'), hashlib.sha256).digest()
    return hmac.compare_digest(signature, base64.b64encode(hash).decode('utf-8'))

def reply_message(reply_token, text):
    url = 'https://api.line.me/v2/bot/message/reply'
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'}
    if len(text) > 4500:
        text = text[:4500] + "..."
    data = {'replyToken': reply_token, 'messages': [{'type': 'text', 'text': text}]}
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req) as res:
            print(f"Reply sent: {res.status}", file=sys.stderr)
    except Exception as e:
        print(f"Reply error: {e}", file=sys.stderr)

@app.route('/', methods=['GET'])
def health_check():
    return 'Mora AI Secretary is running!', 200

@app.route('/webhook', methods=['POST'])
def webhook():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    
    if not verify_signature(body, signature):
        return 'Invalid signature', 400
    
    try:
        data = json.loads(body)
        events = data.get('events', [])
    except:
        return 'OK', 200
    
    for event in events:
        event_type = event.get('type')
        source = event.get('source', {})
        user_id = source.get('userId', 'unknown')
        
        if event_type == 'message':
            message = event.get('message', {})
            message_type = message.get('type')
            
            if message_type == 'text':
                user_text = message.get('text', '')
                reply_token = event.get('replyToken')
                
                print(f"User [{user_id[:8]}]: {user_text}", file=sys.stderr)
                
                ai_response = get_gemini_response(user_id, user_text)
                
                print(f"Mora: {ai_response[:100]}...", file=sys.stderr)
                
                if reply_token:
                    reply_message(reply_token, ai_response)
        
        elif event_type == 'follow':
            reply_token = event.get('replyToken')
            conversation_history[user_id] = []
            if reply_token:
                reply_message(reply_token, "あ、こんにちは！モラです😊\n\n色々お手伝いできますよ〜！\n・ドキュメント作成\n・メール確認\n・計算\n・PDF読み取り\n\n気軽に言ってくださいね！")
    
    return 'OK', 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
