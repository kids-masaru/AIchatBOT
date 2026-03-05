"""
Koto AI Secretary - LINE Bot Entry Point
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
from flask import Flask, request
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

app = Flask(__name__)
# Enable CORS for dashboard - allow all origins and handle preflight
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"], "allow_headers": ["Content-Type"]}})


@app.route('/')
def healthcheck():
    """Health check endpoint for Railway/deployment platforms"""
    return 'KOTO is running!', 200


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


def verify_signature(body, signature):
    """Verify LINE webhook signature"""
    if not LINE_CHANNEL_SECRET:
        return True
    hash_value = hmac.new(
        LINE_CHANNEL_SECRET.encode('utf-8'),
        body.encode('utf-8'),
        hashlib.sha256
    ).digest()
    return hmac.compare_digest(signature, base64.b64encode(hash_value).decode('utf-8'))


def push_message(user_id, texts):
    """Send message via LINE Push API (for async responses)
       texts: string or list of strings
    """
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'
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


def reply_message(reply_token, text):
    """Send message via LINE Reply API (for sync responses)"""
    url = 'https://api.line.me/v2/bot/message/reply'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'
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


def get_line_message_content(message_id):
    """Download message content (image/file) from LINE"""
    # Note: Use api-data.line.me for content
    url = f'https://api-data.line.me/v2/bot/message/{message_id}/content'
    headers = {
        'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'
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
        
        # Pass the combined text to Koto
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
    return 'Koto AI Secretary is running!', 200


@app.route('/webhook', methods=['POST'])
def webhook():
    """LINE webhook endpoint - returns immediately, processes async"""
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    
    if not verify_signature(body, signature):
        return 'Invalid signature', 400
    
    try:
        data = json.loads(body)
        events = data.get('events', [])
    except Exception:
        return 'OK', 200
    
    for event in events:
        event_type = event.get('type')
        source = event.get('source', {})
        user_id = source.get('userId', 'unknown')
        
        if event_type == 'message':
            message = event.get('message', {})
            message_type = message.get('type')
            
            reply_token = event.get('replyToken')
            
            if message_type == 'text':
                user_text = message.get('text', '')
                message_id = message.get('id')
                print(f"User Text [{user_id[:8]} enqueueing]: {user_text} ID: {message_id}", file=sys.stderr)
                enqueue_message(user_id, {
                    'type': 'text',
                    'text': user_text,
                    'message_id': message_id,
                    'reply_token': reply_token
                })
                process_queue_for_user(user_id, process_batched_messages)
                
            elif message_type == 'image':
                message_id = message.get('id')
                print(f"User Image [{user_id[:8]} enqueueing] ID: {message_id}", file=sys.stderr)
                enqueue_message(user_id, {
                    'type': 'image',
                    'message_id': message_id,
                    'reply_token': reply_token
                })
                process_queue_for_user(user_id, process_batched_messages)
                
            elif message_type == 'file':
                message_id = message.get('id')
                filename = message.get('fileName')
                print(f"User File [{user_id[:8]} enqueueing] Name: {filename}", file=sys.stderr)
                enqueue_message(user_id, {
                    'type': 'file',
                    'message_id': message_id,
                    'filename': filename,
                    'reply_token': reply_token
                })
                process_queue_for_user(user_id, process_batched_messages)
        
        elif event_type == 'follow':
            reply_token = event.get('replyToken')
            clear_user_history(user_id)
            if reply_token:
                reply_message(
                    reply_token,
                    "あ、こんにちは！コトです😊\n\n"
                    "色々お手伝いできますよ〜！\n"
                    "・ドキュメント作成\n"
                    "・メール確認\n"
                    "・計算\n"
                    "・PDF読み取り\n"
                    "・Web検索\n\n"
                    "気軽に言ってくださいね！"
                )
    
    # Return immediately - processing happens in background
    return 'OK', 200

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
    """Manual trigger for reminders - Profiler runs in background to avoid timeout"""
    import threading
    
    # 1. Check Reminders (fast, run synchronously)
    try:
        check_reminders()
    except Exception as e:
        print(f"Cron Reminder Error: {e}", file=sys.stderr)
        
    # 2. Run Profiler in background thread (slow, avoid timeout)
    def run_profiler_background():
        try:
            run_profiler()
        except Exception as e:
            print(f"Cron Profiler Error (background): {e}", file=sys.stderr)
    
    profiler_thread = threading.Thread(target=run_profiler_background, daemon=True)
    profiler_thread.start()
    print("Cron: Profiler started in background thread", file=sys.stderr)

    return 'Cron job executed', 200

@app.route('/debug/run-profiler', methods=['POST'])
def debug_run_profiler():
    """Manual trigger for profiler"""
    run_profiler()
    return 'Profiler executed', 200

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
        return json.dumps(load_config(), ensure_ascii=False), 200, {'Content-Type': 'application/json'}
    
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
    
    if request.method == 'GET':
        profile = get_user_profile(target_user_id)
        return json.dumps(profile, ensure_ascii=False), 200, {'Content-Type': 'application/json'}
        
    elif request.method == 'POST':
        try:
            new_profile = request.json
            if save_user_profile(target_user_id, new_profile):
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


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"Starting Koto AI Secretary on port {port}...", file=sys.stderr)
    app.run(host='0.0.0.0', port=port)
