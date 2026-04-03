"""
Mora AI Secretary - LINE Bot Entry Point
Flask server with asynchronous message processing and Config API
"""
import os
import sys
import json
import hashlib
import hmac
import base64
import urllib.request
import threading
from flask import Flask, request, render_template_string
from dotenv import load_dotenv

load_dotenv()

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.agent import get_gemini_response
from utils.storage import clear_user_history
from utils.sheets_config import load_config, save_config
from tools.google_ops import search_drive
from utils.queue import enqueue_message, process_queue_for_user
from flask_cors import CORS
from core.clients import registry

app = Flask(__name__)

# --- Pause/Resume mechanism ---
import time as _time
_paused_clients = {}  # {client_id: expire_timestamp}
PAUSE_DURATION = 1800  # 30 minutes auto-resume

def is_client_paused(client_id):
    """Check if Mora is paused for a client"""
    if client_id not in _paused_clients:
        return False
    if _time.time() > _paused_clients[client_id]:
        del _paused_clients[client_id]
        return False
    return True

def pause_client(client_id, duration=PAUSE_DURATION):
    """Pause Mora for a client"""
    _paused_clients[client_id] = _time.time() + duration
    print(f"Mora PAUSED for client '{client_id}' ({duration}s)", file=sys.stderr)

def resume_client(client_id):
    """Resume Mora for a client"""
    _paused_clients.pop(client_id, None)
    print(f"Mora RESUMED for client '{client_id}'", file=sys.stderr)


def _check_admin_auth(req) -> bool:
    """管理者パスワード認証（クエリパラメータ ?pw= またはリクエストボディの pw フィールド）"""
    password = os.environ.get('ADMIN_PASSWORD', 'admin123')
    return (req.args.get('pw') == password
            or (req.json or {}).get('pw') == password)


@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    """Simple management dashboard for the AIchatBOT fleet"""
    # Simple password protection
    password = os.environ.get('ADMIN_PASSWORD', 'admin123')
    if request.args.get('pw') != password:
        return "Unauthorized: Please provide the correct password via ?pw=PASSWORD", 401
    
    # Manual reload trigger
    if request.args.get('reload') == '1':
        registry.load_registry()
        return "Registry reloaded from Google Sheet", 200
        
    clients = registry.load_registry()
    sheet_id = registry.registry_sheet_id
    
    # Premium UI with inline CSS
    html = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AIchatBOT Admin</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
            body {{
                font-family: 'Inter', system-ui, -apple-system, sans-serif;
                background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
                color: #f8fafc;
                margin: 0;
                padding: 2rem;
                min-height: 100vh;
            }}
            .container {{ max-width: 900px; margin: 0 auto; }}
            .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; }}
            h1 {{
                font-size: 2.25rem;
                font-weight: 700;
                background: linear-gradient(to right, #38bdf8, #818cf8);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin: 0;
            }}
            .card {{
                background: rgba(30, 41, 59, 0.7);
                backdrop-filter: blur(12px);
                border: 1px solid rgba(148, 163, 184, 0.1);
                border-radius: 16px;
                padding: 1.5rem;
                margin-bottom: 1.5rem;
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            }}
            .card h2 {{ font-size: 1.25rem; margin-top: 0; color: #94a3b8; border-bottom: 1px solid rgba(148, 163, 184, 0.1); padding-bottom: 0.75rem; }}
            .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }}
            .stat-box {{ padding: 1rem; background: rgba(15, 23, 42, 0.5); border-radius: 12px; }}
            .stat-value {{ font-size: 1.5rem; font-weight: 700; color: #38bdf8; }}
            .stat-label {{ font-size: 0.875rem; color: #64748b; }}
            
            .client-list {{ list-style: none; padding: 0; margin: 0.5rem 0; }}
            .client-item {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: rgba(15, 23, 42, 0.3);
                padding: 1rem;
                border-radius: 12px;
                margin-bottom: 0.75rem;
                transition: transform 0.2s;
            }}
            .client-item:hover {{ transform: translateX(5px); background: rgba(15, 23, 42, 0.5); }}
            .client-info {{ display: flex; flex-direction: column; }}
            .client-id {{ font-family: monospace; color: #f472b6; font-weight: 600; font-size: 1rem; }}
            .client-name {{ font-size: 0.875rem; color: #94a3b8; margin-top: 0.25rem; }}
            
            .badge {{
                display: inline-block;
                padding: 0.25rem 0.5rem;
                border-radius: 9999px;
                font-size: 0.75rem;
                font-weight: 600;
                background: rgba(56, 189, 248, 0.1);
                color: #38bdf8;
                margin-top: 0.5rem;
            }}

            .btn {{
                background: linear-gradient(to right, #38bdf8, #2563eb);
                color: white;
                padding: 0.75rem 1.5rem;
                border-radius: 10px;
                text-decoration: none;
                font-weight: 600;
                border: none;
                cursor: pointer;
                transition: all 0.2s;
                font-size: 0.875rem;
            }}
            .btn:hover {{ opacity: 0.9; transform: translateY(-1px); }}
            .btn-secondary {{ background: rgba(51, 65, 85, 0.5); color: #94a3b8; }}
            .btn-secondary:hover {{ background: rgba(51, 65, 85, 0.8); }}
            
            .link-icon {{ width: 1.25rem; height: 1.25rem; vertical-align: middle; }}
            .footer {{ text-align: center; color: #475569; font-size: 0.875rem; margin-top: 3rem; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>AIchatBOT Admin</h1>
                <button class="btn" onclick="reloadRegistry()">名簿を再読込</button>
            </div>
            
            <div class="card">
                <h2>📈 システム稼働状況</h2>
                <div class="stats">
                    <div class="stat-box">
                        <div class="stat-label">登録ボット数</div>
                        <div class="stat-value">{len(clients)}</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">マスタ名簿</div>
                        <a href="https://docs.google.com/spreadsheets/d/{sheet_id}/edit" target="_blank" class="link-label" style="color: #38bdf8; text-decoration: none; font-size: 0.875rem; display: block; margin-top: 0.5rem;">🔗 シートを開く</a>
                    </div>
                </div>
            </div>

            <div class="card">
                <h2>🤖 稼働中のボット一覧</h2>
                <ul class="client-list">
                    {"".join([f'''
                    <li class="client-item">
                        <div class="client-info">
                            <span class="client-id">{cid}</span>
                            <span class="client-name">{c.get("bot_name", "名称未設定")}</span>
                            <span class="badge">{c.get("personality", "標準性格")}</span>
                        </div>
                        <a href="https://docs.google.com/spreadsheets/d/{c.get("spreadsheet_id", "")}/edit" target="_blank" class="btn btn-secondary">設定確認</a>
                    </li>
                    ''' for cid, c in clients.items()])}
                </ul>
            </div>

            <div class="footer">
                <p>AIchatBOT Fleet Management System &copy; 2024</p>
                <p style="font-size: 0.75rem;">🔒 パスワード保護されています (ADMIN_PASSWORD)</p>
            </div>
        </div>

        <script>
            function reloadRegistry() {{
                const btn = event.target;
                const originalText = btn.innerText;
                btn.innerText = "読み込み中...";
                btn.disabled = true;
                
                fetch(window.location.search + '&reload=1')
                    .then(res => res.text())
                    .then(msg => {{
                        alert("名簿を更新しました！");
                        location.reload();
                    }})
                    .catch(err => {{
                        alert("エラーが発生しました: " + err);
                        btn.innerText = originalText;
                        btn.disabled = false;
                    }});
            }}
        </script>
    </body>
    </html>
    """
    return render_template_string(html)
# Enable CORS for dashboard - allow all origins and handle preflight
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"], "allow_headers": ["Content-Type"]}})


@app.route('/')
def healthcheck():
    """Health check endpoint for Railway/deployment platforms"""
    return 'MORA is running!', 200


@app.route('/debug/vector-status')
def vector_status():
    """Debug endpoint to check vector store status"""
    import json
    try:
        from utils.vector_store import get_collection_stats
        stats = get_collection_stats()
        return json.dumps(stats, ensure_ascii=False), 200, {'Content-Type': 'application/json'}
    except Exception as e:
        return json.dumps({"error": str(e)}), 500, {'Content-Type': 'application/json'}


# LINE credentials
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET', '')
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', '')


def verify_signature(body, signature, channel_secret):
    """Verify LINE webhook signature"""
    if not channel_secret:
        return False  # T02: secretが未設定のリクエストは拒否
    hash_value = hmac.new(
        channel_secret.encode('utf-8'),
        body.encode('utf-8'),
        hashlib.sha256
    ).digest()
    return hmac.compare_digest(signature, base64.b64encode(hash_value).decode('utf-8'))


def push_message(user_id, texts, channel_access_token):
    """Send message via LINE Push API (for async responses)
       texts: string or list of strings
    """
    if not channel_access_token:
        print(f"Error: No access token for push to {user_id}", file=sys.stderr)
        return

    url = 'https://api.line.me/v2/bot/message/push'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {channel_access_token}'
    }
    
    # Normalize to list
    if isinstance(texts, str):
        texts = [texts]
        
    messages = []
    for text in texts:
        # Truncate if too long
        if len(text) > 4500:
            text = text[:4500] + "..."
        messages.append({'type': 'text', 'text': text})
    
    # Send in chunks of 5 (LINE API limit)
    for i in range(0, len(messages), 5):
        chunk = messages[i:i+5]
        
        data = {
            'to': user_id,
            'messages': chunk
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        
        try:
            with urllib.request.urlopen(req) as res:
                print(f"Push sent to {user_id[:8]}: {res.status}", file=sys.stderr)
        except Exception as e:
            print(f"Push error: {e}", file=sys.stderr)


def reply_message(reply_token, text, channel_access_token):
    """Send message via LINE Reply API (for sync responses)"""
    if not channel_access_token:
        print(f"Error: No access token for reply", file=sys.stderr)
        return

    url = 'https://api.line.me/v2/bot/message/reply'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {channel_access_token}'
    }
    
    if len(text) > 4500:
        text = text[:4500] + "..."
    
    data = {
        'replyToken': reply_token,
        'messages': [{'type': 'text', 'text': text}]
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers=headers,
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req) as res:
            print(f"Reply sent: {res.status}", file=sys.stderr)
    except Exception as e:
        print(f"Reply error: {e}", file=sys.stderr)
        raise e # Re-raise to trigger fallback to Push in caller


def get_line_message_content(message_id, channel_access_token):
    """Download message content (image/file) from LINE"""
    if not channel_access_token: return None
    # Note: Use api-data.line.me for content
    url = f'https://api-data.line.me/v2/bot/message/{message_id}/content'
    headers = {
        'Authorization': f'Bearer {channel_access_token}'
    }
    
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as res:
            return res.read()
    except Exception as e:
        print(f"Content download error: {e}", file=sys.stderr)
        return None


def process_batched_messages(user_id, tasks):
    """Process a batch of queued messages for a user"""
    try:
        print(f"Processing {len(tasks)} batched messages for {user_id[:8]}", file=sys.stderr)
        
        combined_text = ""
        reply_tokens = []
        last_image_data = None
        last_image_mime = None
        
        for task in tasks:
            message_type = task.get('type')
            user_text = task.get('text', '')
            reply_token = task.get('reply_token')
            message_id = task.get('message_id')
            filename = task.get('filename')
            
            if reply_token and reply_token not in reply_tokens:
                reply_tokens.append(reply_token)
                
            if message_type in ['image', 'file']:
                # 1. Download from LINE
                content = get_line_message_content(message_id)
                if not content:
                    print(f"Content download failed for {message_id}", file=sys.stderr)
                    continue
                
                # 2. Determine filename
                import datetime
                import mimetypes
                if not filename:
                    ext = 'jpg' if message_type == 'image' else 'dat'
                    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"line_{timestamp}.{ext}"
                    
                # 3. Upload to Drive
                from tools.google_ops import upload_file_to_drive
                mime = 'image/jpeg' if message_type == 'image' else None 
                if not mime:
                    mime, _ = mimetypes.guess_type(filename)
                if not mime: mime = 'application/octet-stream'
                
                result = upload_file_to_drive(filename, content, mime_type=mime)
                if result.get("success"):
                    file_url = result.get("url")
                    file_id = result.get("file_id")
                    
                    combined_text += f"\n【ファイルアップロード】\nファイル名: {filename}\nファイルID: {file_id}\n保存先URL: {file_url}\n"
                    
                    if message_type == 'image':
                        last_image_data = content
                        last_image_mime = mime
                        combined_text += "※この画像の内容は添付データとして送信されています。\n"
                        
                        from core.agent import analyze_document_layout
                        layout = analyze_document_layout(content, mime)
                        if layout.get("success"):
                            combined_text += f"【ドキュメント構造解析】\n{json.dumps(layout.get('structure') or layout.get('raw', ''), ensure_ascii=False)}\n"
                            
                    elif mime == 'application/pdf':
                        from tools.google_ops import pdf_to_images
                        pdf_images = pdf_to_images(content)
                        if pdf_images:
                            last_image_data, last_image_mime = pdf_images[0]
                            combined_text += f"※このPDFの先頭ページは画像として添付されています。\n"
                            from core.agent import analyze_document_layout
                            layout = analyze_document_layout(last_image_data, last_image_mime)
                            if layout.get("success"):
                                combined_text += f"【PDFレイアウト解析】\n{json.dumps(layout.get('structure') or layout.get('raw', ''), ensure_ascii=False)}\n"
                else:
                    combined_text += f"\n【警告】ファイル '{filename}' の保存に失敗しました（{result.get('error')}）。\n"
                    
            elif message_type == 'text':
                combined_text += f"\nユーザーの発言: {user_text}\n"

        if not combined_text.strip():
            return
            
        print(f"Agent Batched Input: {combined_text}", file=sys.stderr)
        
        # Debug mode callback: sends tool activity to LINE in real-time
        def debug_callback(uid, msg):
            try:
                push_message(uid, f"⚙️ 裏側ログ:\n{msg}")
            except Exception as e:
                print(f"Debug push error: {e}", file=sys.stderr)
        
        # Pass the combined text to Mora
        ai_response = get_gemini_response(
            user_id, 
            combined_text.strip(), 
            image_data=last_image_data, 
            mime_type=last_image_mime,
            on_tool_call=debug_callback
        )
        
        # Try sending response via the latest available reply token
        success = False
        valid_reply_token = reply_tokens[-1] if reply_tokens else None
        
        if valid_reply_token:
            try:
                reply_message(valid_reply_token, ai_response)
                success = True
            except Exception as e:
                print(f"Reply failed, trying Push: {e}", file=sys.stderr)
                
        if not success:
            push_message(user_id, ai_response)
            
    except Exception as e:
        print(f"Batched async processing error: {e}", file=sys.stderr)
        try:
            push_message(user_id, "ごめんなさい、エラーが出ちゃいました...😢")
        except:
            pass



@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return 'Mora AI Secretary is running!', 200


@app.route('/callback/<client_id>', methods=['POST'])
def callback(client_id):
    """Multi-tenant LINE webhook endpoint"""
    client_config = registry.get_client(client_id)
    if not client_config:
        return 'Client not found', 404
    
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    
    if not verify_signature(body, signature, client_config['line_channel_secret']):
        return 'Invalid signature', 400
    
    try:
        data = json.loads(body)
        events = data.get('events', [])
    except Exception:
        return 'OK', 200
    
    # Process events with client context
    for event in events:
        process_line_event(event, client_config)
    
    return 'OK', 200


@app.route('/webhook', methods=['POST'])
def webhook():
    """Default legacy webhook endpoint"""
    return callback('default')


def process_line_event(event, client_config):
    """Process a single LINE event with specific client config"""
    event_type = event.get('type')
    source = event.get('source', {})
    user_id = source.get('userId', 'unknown')
    client_id = client_config.get('client_id', 'default')

    if event_type == 'message':
        message = event.get('message', {})
        message_type = message.get('type')
        reply_token = event.get('replyToken')
        text = message.get('text', '').strip()
        token = client_config.get('line_channel_access_token', '')

        # --- Admin commands (from Izaki) ---
        izaki_id = os.environ.get('IZAKI_LINE_USER_ID', '')
        if user_id == izaki_id and message_type == 'text':
            if text in ['停止', 'stop', 'ストップ']:
                pause_client(client_id)
                if reply_token:
                    reply_message(reply_token, f"⏸ Mora一時停止しました（{client_id}）\n30分後に自動復帰します\n\n「再開」で手動復帰できます", token)
                return
            elif text in ['再開', 'resume', '再開する']:
                resume_client(client_id)
                if reply_token:
                    reply_message(reply_token, f"▶ Mora再開しました（{client_id}）", token)
                return

        # --- Skip if paused ---
        if is_client_paused(client_id):
            print(f"Mora is PAUSED for {client_id}, skipping message from {user_id[:8]}", file=sys.stderr)
            return

        # Enqueue with client context
        task = {
            'client_id': client_id,
            'type': message_type,
            'reply_token': reply_token,
            'message_id': message.get('id'),
            'text': message.get('text', ''),
            'filename': message.get('fileName')
        }

        enqueue_message(user_id, task)

        # Process queue in background
        def run_async():
            process_queue_for_user(user_id, lambda uid, tasks: process_batched_messages(uid, tasks, client_config))

        threading.Thread(target=run_async, daemon=True).start()
        
    elif event_type == 'follow':
        reply_token = event.get('replyToken')
        clear_user_history(user_id)
        if reply_token:
            bot_name = client_config.get('bot_name', 'AIchatBOT')
            reply_message(
                reply_token,
                f"こんにちは！{bot_name}です😊\n\n"
                "何かお手伝いしましょうか？",
                client_config['line_channel_access_token']
            )


def process_batched_messages(user_id, tasks, client_config):
    """Process a batch of queued messages for a user with client context"""
    try:
        token = client_config['line_channel_access_token']
        combined_text = ""
        reply_tokens = []
        last_image_data = None
        last_image_mime = None

        for task in tasks:
            message_type = task.get('type')
            reply_token = task.get('reply_token')
            message_id = task.get('message_id')
            filename = task.get('filename')

            if reply_token and reply_token not in reply_tokens:
                reply_tokens.append(reply_token)

            if message_type == 'text':
                combined_text += f"\nユーザー: {task['text']}\n"

            elif message_type == 'image':
                content = get_line_message_content(message_id, token)
                if content:
                    last_image_data = content
                    last_image_mime = 'image/jpeg'
                    combined_text += "\n【画像が送られました。内容を確認して自然に返答してください。】\n"
                else:
                    print(f"Image download failed for {message_id}", file=sys.stderr)

            elif message_type == 'file':
                content = get_line_message_content(message_id, token)
                if content:
                    import datetime, mimetypes
                    if not filename:
                        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"line_{timestamp}.dat"
                    mime, _ = mimetypes.guess_type(filename) if filename else (None, None)
                    if not mime:
                        mime = 'application/octet-stream'
                    from tools.google_ops import upload_file_to_drive
                    result = upload_file_to_drive(filename, content, mime_type=mime)
                    if result.get("success"):
                        combined_text += f"\n【ファイル受信】ファイル名: {filename} (Drive保存済み)\n"
                    else:
                        combined_text += f"\n【ファイル受信失敗】{filename}\n"

        if not combined_text.strip() and last_image_data is None:
            return

        if not combined_text.strip():
            combined_text = "【画像が送られました。内容を確認して自然に返答してください。】"

        # Call AI
        ai_response = get_gemini_response(
            user_id,
            combined_text.strip(),
            image_data=last_image_data,
            mime_type=last_image_mime,
            client_config=client_config
        )

        # Reply
        if reply_tokens:
            reply_message(reply_tokens[-1], ai_response, token)
        else:
            push_message(user_id, ai_response, token)

    except Exception as e:
        print(f"Batch processing error: {e}", file=sys.stderr)

# Initialize Scheduler
def check_reminders():
    """Scheduled job to check and send reminders (Manual Trigger Only)"""
    # Use existing cron logic but internalize the context
    with app.app_context():
        try:
            # Reusing the logic from the old route, but suited for internal execution
            from utils.user_db import get_active_users
            users = get_active_users()
            print(f"Scheduler: Checking reminders for {len(users)} users...", file=sys.stderr)
            
            for user in users:
                process_user_reminders(user)
                
        except Exception as e:
            print(f"Scheduler Error: {e}", file=sys.stderr)

def process_user_reminders(user):
    """Process reminders for a single user"""
    user_id = user['user_id']
    location = user['location']
    
    auth_config = load_config()
    reminders = auth_config.get('reminders', [])
    
    # Clean up fallback: Only use fallback if reminders is strictly None or empty,
    # AND we have legacy config values we want to honor.
    # But ideally we trust the list. If list is empty, it means no reminders.
    
    from datetime import datetime, timezone, timedelta
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)
    current_hour = now.hour
    
    print(f"Checking reminders for {user_id[:8]} at {current_hour}:00", file=sys.stderr)

    for reminder in reminders:
        if not reminder.get('enabled', True): continue
        
        r_time = reminder.get('time', '07:00')
        try:
            r_hour = int(r_time.split(':')[0])
        except:
            r_hour = 7
            
        # Match current hour
        if r_hour != current_hour:
             continue
        
        send_reminder(user_id, location, reminder)

def send_reminder(user_id, location, reminder):
    from datetime import datetime, timezone, timedelta
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)
    today_str = now.strftime('%Y年%m月%d日')
    
    # Get prompt entirely from config - no hardcoded structure
    # The prompt in config should include any formatting instructions the user wants
    config_prompt = reminder.get('prompt', '今日の天気と予定を教えて')
    
    # Only inject date and location context, let config control everything else
    prompt = f"現在は日本時間の {today_str} です。場所は{location}です。\n\n{config_prompt}"
    
    try:
        response = get_gemini_response(user_id, prompt)
        
        # Check if config specifies a separator for multi-message splitting
        separator = reminder.get('separator', None)
        if separator and separator in response:
            messages = [msg.strip() for msg in response.split(separator) if msg.strip()]
        else:
            messages = [response]
        
        # Add greeting based on time (this is behavior, not content - stays in code)
        h = now.hour
        if messages:
            first_msg = messages[0]
            if h < 12 and "おはよう" not in first_msg:
                messages[0] = f"おはようございます！☀️\n\n{first_msg}"
            elif h >= 18 and "こんばんは" not in first_msg:
                messages[0] = f"こんばんは！🌙\n\n{first_msg}"
            
        push_message(user_id, messages)
        print(f"Sent reminder to {user_id[:8]}", file=sys.stderr)
    except Exception as e:
        print(f"Failed to send reminder: {e}", file=sys.stderr)


# Start Scheduler
# Profiler Job (Manual Trigger Only)
def run_profiler():
    """Run profiler for all active users"""
    with app.app_context():
        try:
            from core.profiler import profiler
            from utils.user_db import get_active_users
            
            users = get_active_users()
            print(f"Profiler: Starting daily analysis for {len(users)} users...", file=sys.stderr)
            
            for user in users:
                user_id = user['user_id']
                # Run profile analysis
                profiler.run_analysis(user_id)
                
        except Exception as e:
            print(f"Profiler Job Error: {e}", file=sys.stderr)

# Scheduler removed
# scheduler = BackgroundScheduler() ...


@app.route('/cron', methods=['GET'])
def cron_job():
    """Background jobs are disabled for AIchatBOT."""
    print("Cron: Background jobs are currently disabled.", file=sys.stderr)
    return 'Cron disabled', 200

@app.route('/debug/run-profiler', methods=['POST'])
def debug_run_profiler():
    """Manual trigger for profiler"""
    run_profiler()
    return 'Profiler executed', 200

# ─── T19: エスカレーション管理 API ────────────────────────────────────────────

# ─── T22: Google Meet議事録 API ───────────────────────────────────────────────

@app.route('/admin/minutes/process', methods=['POST'])
def process_meeting_minutes():
    """
    MEET_TRANSCRIPT_FOLDERの新しい文字起こしを処理して議事録を生成し、
    IZAKI_LINE_USER_IDにLINEで送信する（管理者認証必須）。
    手動実行 or スケジューラーから呼び出す。
    """
    if not _check_admin_auth(request):
        return json.dumps({"error": "Unauthorized"}), 401, {'Content-Type': 'application/json'}

    if not os.environ.get("MEET_TRANSCRIPT_FOLDER_ID"):
        return json.dumps({"error": "MEET_TRANSCRIPT_FOLDER_IDが未設定です"}), 503, {'Content-Type': 'application/json'}

    izaki_id = os.environ.get('IZAKI_LINE_USER_ID')
    default_config = registry.get_client('default') or {}
    token = default_config.get('line_channel_access_token') or os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', '')

    from utils.meeting_minutes import process_new_transcripts
    processed = process_new_transcripts(notify_line_user_id=izaki_id, access_token=token)

    return json.dumps({
        "processed": processed,
        "count": len(processed)
    }, ensure_ascii=False), 200, {'Content-Type': 'application/json'}

# ─── T19: エスカレーション管理 API ────────────────────────────────────────────

@app.route('/admin/escalations', methods=['GET'])
def list_escalations():
    """未回答のエスカレーション一覧を返す（管理者認証必須）"""
    if not _check_admin_auth(request):
        return json.dumps({"error": "Unauthorized"}), 401, {'Content-Type': 'application/json'}

    from utils.escalation import get_pending_escalations
    escalations = get_pending_escalations()
    return json.dumps(escalations, ensure_ascii=False), 200, {'Content-Type': 'application/json'}

# ─── T21: フィードバック API ──────────────────────────────────────────────────

@app.route('/admin/feedback', methods=['GET'])
def list_feedback():
    """フィードバック未評価の回答一覧（管理者認証必須）"""
    if not _check_admin_auth(request):
        return json.dumps({"error": "Unauthorized"}), 401, {'Content-Type': 'application/json'}

    if not os.environ.get("FEEDBACK_SHEET_ID"):
        return json.dumps({"error": "FEEDBACK_SHEET_IDが未設定です"}), 503, {'Content-Type': 'application/json'}

    try:
        from utils.feedback import _get_sheet_service
        service = _get_sheet_service()
        if not service:
            return json.dumps({"error": "Sheet接続エラー"}), 500, {'Content-Type': 'application/json'}
        result = service.spreadsheets().values().get(
            spreadsheetId=os.environ.get("FEEDBACK_SHEET_ID"),
            range='A:H'
        ).execute()
        rows = result.get('values', [])[1:]
        pending = [
            {'id': r[0], 'timestamp': r[1], 'client_id': r[2],
             'question': r[4] if len(r) > 4 else '', 'response': r[5] if len(r) > 5 else ''}
            for r in rows if len(r) >= 7 and not r[6]
        ]
        return json.dumps(pending, ensure_ascii=False), 200, {'Content-Type': 'application/json'}
    except Exception as e:
        return json.dumps({"error": str(e)}), 500, {'Content-Type': 'application/json'}

@app.route('/admin/feedback/<feedback_id>', methods=['POST'])
def submit_feedback(feedback_id):
    """フィードバックを記録する（管理者認証必須）
    Body: {"pw": "...", "rating": "○" or "×", "comment": "（×の場合の修正内容）"}
    """
    if not _check_admin_auth(request):
        return json.dumps({"error": "Unauthorized"}), 401, {'Content-Type': 'application/json'}

    data = request.json or {}
    rating = data.get('rating', '').strip()
    if rating not in ('○', '×'):
        return json.dumps({"error": "rating must be ○ or ×"}), 400, {'Content-Type': 'application/json'}

    from utils.feedback import record_feedback
    success = record_feedback(feedback_id, rating, data.get('comment', ''))
    if success:
        return json.dumps({"success": True}), 200, {'Content-Type': 'application/json'}
    return json.dumps({"error": "Feedback not found"}), 404, {'Content-Type': 'application/json'}

@app.route('/admin/feedback/digest', methods=['POST'])
def send_feedback_digest():
    """未評価の回答を井崎さんのLINEに日次ダイジェストで送る（管理者認証必須）"""
    if not _check_admin_auth(request):
        return json.dumps({"error": "Unauthorized"}), 401, {'Content-Type': 'application/json'}

    izaki_id = os.environ.get('IZAKI_LINE_USER_ID')
    if not izaki_id:
        return json.dumps({"error": "IZAKI_LINE_USER_ID未設定"}), 503, {'Content-Type': 'application/json'}

    from utils.feedback import _get_sheet_service
    service = _get_sheet_service()
    if not service:
        return json.dumps({"error": "Sheet接続エラー"}), 500, {'Content-Type': 'application/json'}

    result = service.spreadsheets().values().get(
        spreadsheetId=os.environ.get("FEEDBACK_SHEET_ID", ""),
        range='A:H'
    ).execute()
    rows = [r for r in result.get('values', [])[1:] if len(r) >= 7 and not r[6]][:5]  # 最大5件

    if not rows:
        return json.dumps({"message": "未評価なし"}), 200, {'Content-Type': 'application/json'}

    lines = ["【フィードバック依頼】未評価の回答があります\n"]
    for row in rows:
        fb_id = row[0]
        q = row[4][:80] if len(row) > 4 else ''
        r = row[5][:80] if len(row) > 5 else ''
        lines.append(f"▶ {fb_id}\nQ: {q}\nA: {r}\n評価: 「{fb_id} ○」または「{fb_id} × 修正内容」")

    default_config = registry.get_client('default') or {}
    token = default_config.get('line_channel_access_token') or os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', '')
    push_message(izaki_id, "\n\n".join(lines), token)
    return json.dumps({"success": True, "sent": len(rows)}), 200, {'Content-Type': 'application/json'}

# ─── T20: 問い合わせレポート API ─────────────────────────────────────────────

@app.route('/admin/report', methods=['GET'])
def inquiry_report():
    """問い合わせレポートを生成して返す（管理者認証必須）
    クエリパラメータ:
      ?period=weekly|monthly  （デフォルト: weekly）
      ?client_id=xxx          （省略時は全クライアント）
      ?send_line=1            （1を指定すると井崎さんのLINEにも送信）
    """
    if not _check_admin_auth(request):
        return json.dumps({"error": "Unauthorized"}), 401, {'Content-Type': 'application/json'}

    from utils.inquiry_log import generate_report
    period = request.args.get('period', 'weekly')
    target_client = request.args.get('client_id', None)
    report_text = generate_report(client_id=target_client, period=period)

    # LINE送信オプション
    if request.args.get('send_line') == '1':
        izaki_id = os.environ.get('IZAKI_LINE_USER_ID')
        if izaki_id:
            default_config = registry.get_client('default') or {}
            token = default_config.get('line_channel_access_token') or os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', '')
            if token:
                push_message(izaki_id, report_text, token)

    return json.dumps({"report": report_text}, ensure_ascii=False), 200, {'Content-Type': 'application/json'}

@app.route('/admin/escalations/<escalation_id>/resolve', methods=['POST'])
def resolve_escalation_endpoint(escalation_id):
    """エスカレーションに回答し、元ユーザーへ送信する（管理者認証必須）"""
    if not _check_admin_auth(request):
        return json.dumps({"error": "Unauthorized"}), 401, {'Content-Type': 'application/json'}

    data = request.json or {}
    answer = data.get('answer', '').strip()
    if not answer:
        return json.dumps({"error": "answer is required"}), 400, {'Content-Type': 'application/json'}

    from utils.escalation import resolve_escalation
    success = resolve_escalation(escalation_id, answer)
    if success:
        return json.dumps({"success": True}), 200, {'Content-Type': 'application/json'}
    return json.dumps({"error": "Escalation not found or already resolved"}), 404, {'Content-Type': 'application/json'}

@app.route('/debug/ingest', methods=['GET', 'POST'])
def debug_ingest():
    """Manual trigger for knowledge ingestion (Librarian)"""
    try:
        from tools.ingest_knowledge import run_ingestion
        # Note: This might timeout on Vercel if many files. 
        # Ideally should be async or limited batch.
        run_ingestion()
        return 'Ingestion started/completed', 200
    except Exception as e:
        return f'Ingestion failed: {e}', 500


@app.route('/api/config', methods=['GET', 'POST', 'OPTIONS'])
def handle_config():
    """Get or update configuration"""
    # Handle preflight request
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    if request.method == 'GET':
        config = load_config()
        # Add Spreadsheet URL for dashboard link
        try:
            from utils.sheets_config import get_or_create_config_sheet
            sheet_id = get_or_create_config_sheet()
            if sheet_id:
                config["spreadsheet_url"] = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
        except:
            pass
        return json.dumps(config, ensure_ascii=False), 200, {'Content-Type': 'application/json'}
    
    elif request.method == 'POST':
        try:
            new_config = request.json
            if save_config(new_config):
                return json.dumps({"success": True, "config": new_config}), 200, {'Content-Type': 'application/json'}
            else:
                return json.dumps({"error": "Failed to save config"}), 500, {'Content-Type': 'application/json'}
        except Exception as e:
            return json.dumps({"error": str(e)}), 400, {'Content-Type': 'application/json'}

@app.route('/api/agent-logs', methods=['GET', 'OPTIONS'])
def handle_agent_logs():
    """Get recent agent activity logs for dashboard"""
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    try:
        from utils.agent_log import get_logs
        limit = request.args.get('limit', 20, type=int)
        logs = get_logs(limit)
        return json.dumps({"logs": logs}, ensure_ascii=False), 200, {'Content-Type': 'application/json'}
    except Exception as e:
        return json.dumps({"error": str(e)}), 500, {'Content-Type': 'application/json'}

@app.route('/api/profile', methods=['GET', 'POST', 'OPTIONS'])
def handle_profile():
    """Get or update User Profile (Psychological Data)"""
    # Handle preflight request
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    # Authenticate via config (simplified for single-user context)
    # Ideally should get user_id from token, but we are using LINE user ID.
    # We'll fetch the FIRST active user from user_db for dashboard purposes.
    from utils.user_db import get_active_users
    from utils.vector_store import get_user_profile, save_user_profile
    
    users = get_active_users()
    if not users:
        return json.dumps({"error": "No active users found"}), 404, {'Content-Type': 'application/json'}
    
    # Default to the first user found (Single user mode assumption)
    target_user_id = request.args.get('user_id', users[0]['user_id'])
    profile_client_id = request.args.get('client_id', 'default')

    if request.method == 'GET':
        profile = get_user_profile(target_user_id, client_id=profile_client_id)
        return json.dumps(profile, ensure_ascii=False), 200, {'Content-Type': 'application/json'}

    elif request.method == 'POST':
        try:
            new_profile = request.json
            if save_user_profile(target_user_id, new_profile, client_id=profile_client_id):
                return json.dumps({"success": True, "profile": new_profile}), 200, {'Content-Type': 'application/json'}
            else:
                return json.dumps({"error": "Failed to save profile"}), 500, {'Content-Type': 'application/json'}
        except Exception as e:
            return json.dumps({"error": str(e)}), 400, {'Content-Type': 'application/json'}

@app.route('/api/folders', methods=['GET', 'OPTIONS'])
def list_folders():
    """List Google Drive folders for selection (Navigation support)"""
    # Handle preflight request
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    query = request.args.get('q', '')
    parent_id = request.args.get('parentId')
    
    try:
        from utils.auth import get_google_credentials
        from googleapiclient.discovery import build
        
        creds = get_google_credentials()
        if not creds:
             return json.dumps({"error": "Auth failed"}), 401, {'Content-Type': 'application/json'}
             
        service = build('drive', 'v3', credentials=creds)
        
        # Base filter: folders only, not trashed
        q_filter = "mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        
        if parent_id:
            # Navigate into specific folder
            q_filter += f" and '{parent_id}' in parents"
        elif query:
            # Search mode (global)
            # Escape single quotes
            safe_query = query.replace("'", "\\'")
            q_filter += f" and name contains '{safe_query}'"
        else:
            # Default: Root folder
            q_filter += " and 'root' in parents"
            
        results = service.files().list(
            q=q_filter,
            pageSize=50,
            fields="files(id, name)",
            orderBy="folder,name",
            includeItemsFromAllDrives=True,
            supportsAllDrives=True
        ).execute()
        
        folders = results.get('files', [])
        return json.dumps({"folders": folders}), 200, {'Content-Type': 'application/json'}
        
    except Exception as e:
        return json.dumps({"error": str(e)}), 500, {'Content-Type': 'application/json'}


@app.route('/api/skills', methods=['GET', 'OPTIONS'])
def list_skills():
    """List skills from Google Drive MORA_SKILLS folder"""
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    try:
        config = load_config()
        folder_id = config.get("skills_folder_id")
        
        if not folder_id:
             # Try search if ID missing
             from tools.google_ops import search_drive
             res = search_drive("MORA_SKILLS")
             folders = [f for f in res.get("files", []) if f.get("mimeType") == "application/vnd.google-apps.folder"]
             if folders:
                 folder_id = folders[0]["id"]
             else:
                 return json.dumps({"skills": [], "message": "No skills folder found"}), 200, {'Content-Type': 'application/json'}

        from utils.auth import get_google_credentials
        from googleapiclient.discovery import build
        creds = get_google_credentials()
        service = build('drive', 'v3', credentials=creds)
        
        results = service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="files(id, name, description, webViewLink)",
            orderBy="name"
        ).execute()
        
        skills = results.get('files', [])
        return json.dumps({"skills": skills}), 200, {'Content-Type': 'application/json'}
        
    except Exception as e:
        return json.dumps({"error": str(e)}), 500, {'Content-Type': 'application/json'}


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"Starting Mora AI Secretary on port {port}...", file=sys.stderr)
    app.run(host='0.0.0.0', port=port)
