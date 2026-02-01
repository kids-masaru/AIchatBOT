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


def process_message_async(user_id, user_text, reply_token=None, message_id=None, message_type='text', filename=None):
    """Process message (text or file) in background"""
    try:
        print(f"Processing {message_type} from {user_id[:8]}", file=sys.stderr)
        
        # Handle File Uploads
        if message_type in ['image', 'file']:
            reply_token_used = False
            
            # 1. Download from LINE
            content = get_line_message_content(message_id)
            if not content:
                print(f"Content download failed for {message_id}", file=sys.stderr)
                if reply_token:
                    reply_message(reply_token, "ごめんなさい、ファイルのダウンロードに失敗しました...😢")
                return
            
            print(f"Downloaded content: {len(content)} bytes type: {type(content)}", file=sys.stderr)

            # 2. Determine filename
            import datetime
            import mimetypes
            
            if not filename:
                ext = 'jpg' if message_type == 'image' else 'dat'
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"line_{timestamp}.{ext}"

            # 3. Upload to Drive
            from tools.google_ops import upload_file_to_drive
            
            # Detect MIME
            mime = 'image/jpeg' if message_type == 'image' else None 
            if not mime:
                mime, _ = mimetypes.guess_type(filename)
                
            if not mime: mime = 'application/octet-stream' # Fallback
            
            print(f"Uploading {filename} (mime={mime})", file=sys.stderr)
            result = upload_file_to_drive(filename, content, mime_type=mime)
            
            if result.get("success"):
                file_url = result.get("url")
                file_id = result.get("file_id")
                # User didn't say anything, but the act of uploading is the message.
                # format as a system notification to the agent
                # Include File ID for Maker Agent
                user_text = f"【システム通知】ユーザーがファイルをアップロードしました。\nファイル名: {filename}\nファイルID: {file_id}\n保存先URL: {file_url}\n\nこのファイルはGoogle Driveに保存されました。Maker Agentを使って内容を読んだり要約したりできます。"
                
                # If it's an image, pass content to Gemini for immediate understanding
                image_data = None
                image_mime = None
                layout_analysis = None
                
                if message_type == 'image':
                    image_data = content
                    image_mime = mime
                    user_text += "\nまた、この画像の内容は添付データとして送信されています。何が写っているか聞かれたら答えてください。"
                    
                    # Perform document layout analysis for better recreation
                    from core.agent import analyze_document_layout
                    print("Analyzing document layout...", file=sys.stderr)
                    layout_analysis = analyze_document_layout(content, mime)
                    if layout_analysis.get("success"):
                        if layout_analysis.get("structure"):
                            user_text += f"\n\n【ドキュメント構造解析結果】\n```json\n{json.dumps(layout_analysis['structure'], ensure_ascii=False, indent=2)}\n```"
                        else:
                            user_text += f"\n\n【ドキュメント構造解析結果】\n{layout_analysis.get('raw', '')}"
                        user_text += "\n\n★ユーザーが「同じ形式で作って」と言った場合は、上記の構造解析結果を参考に、レイアウトを可能な限り忠実に再現してください。"
                        print("Layout analysis completed", file=sys.stderr)
                
                # If it's a PDF, convert to image for visual analysis
                elif mime == 'application/pdf':
                    from tools.google_ops import pdf_to_images
                    pdf_images = pdf_to_images(content)
                    if pdf_images:
                        # Use first page as the visual reference
                        image_data, image_mime = pdf_images[0]
                        user_text += f"\nまた、このPDFは画像に変換されて添付されています（{len(pdf_images)}ページ）。見た目やレイアウトを参考にできます。"
                        print(f"PDF converted to {len(pdf_images)} images for vision", file=sys.stderr)
                        
                        # Perform document layout analysis for PDF too
                        from core.agent import analyze_document_layout
                        print("Analyzing PDF document layout...", file=sys.stderr)
                        layout_analysis = analyze_document_layout(image_data, image_mime)
                        if layout_analysis.get("success"):
                            if layout_analysis.get("structure"):
                                user_text += f"\n\n【ドキュメント構造解析結果】\n```json\n{json.dumps(layout_analysis['structure'], ensure_ascii=False, indent=2)}\n```"
                            else:
                                user_text += f"\n\n【ドキュメント構造解析結果】\n{layout_analysis.get('raw', '')}"
                            user_text += "\n\n★ユーザーが「同じ形式で作って」と言った場合は、上記の構造解析結果を参考に、レイアウトを可能な限り忠実に再現してください。"
                            print("PDF layout analysis completed", file=sys.stderr)

            else:
                error = result.get("error", "Unknown error")
                print(f"Upload failed: {error}", file=sys.stderr)
                if reply_token:
                    reply_message(reply_token, f"ドライブへの保存に失敗しました...😢\n{error}")
                return

        # Normal Agent Flow (Text or converted System Text)
        print(f"Agent Input: {user_text}", file=sys.stderr)
        
        # Pass image data if available
        ai_response = get_gemini_response(user_id, user_text, image_data=locals().get('image_data'), mime_type=locals().get('image_mime'))
        
        print(f"Koto response: {ai_response[:100]}...", file=sys.stderr)
        
        # Try Reply API first
        success = False
        if reply_token:
            try:
                reply_message(reply_token, ai_response)
                success = True
            except Exception as e:
                 # Token might have expired during upload/processing
                print(f"Reply failed, trying Push: {e}", file=sys.stderr)
        
        # Fallback to Push
        if not success:
            push_message(user_id, ai_response)
            
    except Exception as e:
        print(f"Async processing error: {e}", file=sys.stderr)
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
                print(f"User Text [{user_id[:8]}]: {user_text}", file=sys.stderr)
                # Run in background thread to return 200 OK immediately
                thread = threading.Thread(
                    target=process_message_async,
                    args=(user_id, user_text, reply_token)
                )
                thread.start()
                
            elif message_type == 'image':
                message_id = message.get('id')
                print(f"User Image [{user_id[:8]}] ID: {message_id}", file=sys.stderr)
                thread = threading.Thread(
                    target=process_message_async,
                    args=(user_id, "", reply_token, message_id, 'image')
                )
                thread.start()
                
            elif message_type == 'file':
                message_id = message.get('id')
                filename = message.get('fileName')
                print(f"User File [{user_id[:8]}] Name: {filename}", file=sys.stderr)
                thread = threading.Thread(
                    target=process_message_async,
                    args=(user_id, "", reply_token, message_id, 'file', filename)
                )
                thread.start()
        
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
