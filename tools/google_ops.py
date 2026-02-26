"""
Google Workspace operations - Docs, Sheets, Slides, Drive, Gmail
"""
import sys
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from utils.auth import get_google_credentials, get_shared_folder_id


def move_to_shared_folder(file_id):
    """
    Move a file to the shared folder specified in GOOGLE_DRIVE_FOLDER_ID
    This makes files created by Service Account visible to users
    """
    folder_id = get_shared_folder_id()
    if not folder_id:
        print("Warning: GOOGLE_DRIVE_FOLDER_ID not set. File will be in Service Account's root.", file=sys.stderr)
        return {"success": True, "note": "Shared folder not configured"}
    
    try:
        creds = get_google_credentials()
        if not creds:
            return {"success": False, "error": "Credential error during move"}
        
        drive_service = build('drive', 'v3', credentials=creds)
        
        # Get current parents (supportsAllDrives=True needed for Shared Drives)
        file = drive_service.files().get(
            fileId=file_id, 
            fields='parents',
            supportsAllDrives=True
        ).execute()
        previous_parents = ",".join(file.get('parents', []))
        
        # Move to shared folder
        drive_service.files().update(
            fileId=file_id,
            addParents=folder_id,
            removeParents=previous_parents,
            fields='id, parents',
            supportsAllDrives=True
        ).execute()
        
        print(f"Moved file {file_id} to shared folder {folder_id}", file=sys.stderr)
        return {"success": True}
    except Exception as e:
        print(f"Error moving to shared folder: {e}", file=sys.stderr)
        return {"success": False, "error": str(e)}


def create_google_doc(title, content=""):
    """Create a Google Doc directly in the shared folder"""
    try:
        creds = get_google_credentials()
        if not creds:
            return {"error": "Google認証に失敗しました。環境変数を確認してください。"}
        
        drive_service = build('drive', 'v3', credentials=creds)
        docs_service = build('docs', 'v1', credentials=creds)
        
        folder_id = get_shared_folder_id()
        file_metadata = {
            'name': title,
            'mimeType': 'application/vnd.google-apps.document'
        }
        
        # If shared folder is set, create directly inside it
        if folder_id:
            file_metadata['parents'] = [folder_id]
        
        # 1. Create file using Drive API
        file = drive_service.files().create(
            body=file_metadata,
            fields='id',
            supportsAllDrives=True
        ).execute()
        doc_id = file.get('id')
        
        # 2. Insert content using Docs API
        if content:
            requests = [{'insertText': {'location': {'index': 1}, 'text': content}}]
            docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
        
        url = f"https://docs.google.com/document/d/{doc_id}/edit"
        return {"success": True, "title": title, "url": url, "id": doc_id}
    except Exception as e:
        print(f"Docs error: {e}", file=sys.stderr)
        return {"error": f"ドキュメント作成中にエラーが発生しました: {str(e)}"}


def create_google_sheet(title, data=None):
    """Create a Google Sheet directly in the shared folder"""
    try:
        creds = get_google_credentials()
        if not creds:
            return {"error": "Google認証に失敗しました。環境変数を確認してください。"}
        
        drive_service = build('drive', 'v3', credentials=creds)
        sheets_service = build('sheets', 'v4', credentials=creds)
        
        folder_id = get_shared_folder_id()
        file_metadata = {
            'name': title,
            'mimeType': 'application/vnd.google-apps.spreadsheet'
        }
        
        if folder_id:
            file_metadata['parents'] = [folder_id]
            
        # 1. Create using Drive API
        file = drive_service.files().create(
            body=file_metadata,
            fields='id',
            supportsAllDrives=True
        ).execute()
        sheet_id = file.get('id')
        
        # 2. Update content using Sheets API
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
        return {"error": f"スプレッドシート作成中にエラーが発生しました: {str(e)}"}


def create_google_slide(title, pages=None):
    """Create a Google Slides presentation directly in the shared folder
    
    Args:
        title: Title of the presentation
        pages: List of dicts [{'title': 'Slide 1', 'body': 'Content...'}, ...]
    """
    try:
        creds = get_google_credentials()
        if not creds:
            return {"error": "Google認証に失敗しました。環境変数を確認してください。"}
        
        drive_service = build('drive', 'v3', credentials=creds)
        slides_service = build('slides', 'v1', credentials=creds)
        
        folder_id = get_shared_folder_id()
        file_metadata = {
            'name': title,
            'mimeType': 'application/vnd.google-apps.presentation'
        }
        
        if folder_id:
            file_metadata['parents'] = [folder_id]
            
        file = drive_service.files().create(
            body=file_metadata,
            fields='id',
            supportsAllDrives=True
        ).execute()
        pres_id = file.get('id')
        
        # If pages provided, add them
        if pages:
            requests = []
            for i, page in enumerate(pages):
                slide_id = f"slide_{i}"
                title_id = f"title_{i}"
                body_id = f"body_{i}"
                
                # 1. Create Slide
                requests.append({
                    'createSlide': {
                        'objectId': slide_id,
                        'slideLayoutReference': {'predefinedLayout': 'TITLE_AND_BODY'},
                        'placeholderIdMappings': [
                            {'layoutPlaceholder': {'type': 'TITLE'}, 'objectId': title_id},
                            {'layoutPlaceholder': {'type': 'BODY'}, 'objectId': body_id},
                        ]
                    }
                })
                
                # 2. Insert Title
                if page.get('title'):
                    requests.append({
                        'insertText': {
                            'objectId': title_id,
                            'text': page['title']
                        }
                    })
                    
                # 3. Insert Body
                if page.get('body'):
                    requests.append({
                        'insertText': {
                            'objectId': body_id,
                            'text': page['body']
                        }
                    })
            
            if requests:
                slides_service.presentations().batchUpdate(
                    presentationId=pres_id, 
                    body={'requests': requests}
                ).execute()
        
        url = f"https://docs.google.com/presentation/d/{pres_id}/edit"
        return {"success": True, "title": title, "url": url, "id": pres_id}
    except Exception as e:
        return {"error": f"スライド作成中にエラーが発生しました: {str(e)}"}


def create_drive_folder(folder_name):
    """Create a new folder in Google Drive (shared folder if configured)"""
    try:
        creds = get_google_credentials()
        if not creds:
             return {"error": "Google認証に失敗しました。"}
             
        drive_service = build('drive', 'v3', credentials=creds)
        
        folder_id = get_shared_folder_id()
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        if folder_id:
            file_metadata['parents'] = [folder_id]
            
        file = drive_service.files().create(
            body=file_metadata,
            fields='id, webViewLink',
            supportsAllDrives=True
        ).execute()
        
        return {
            "success": True, 
            "folder_name": folder_name, 
            "id": file.get('id'),
            "url": file.get('webViewLink')
        }
    except Exception as e:
        return {"error": f"フォルダ作成中にエラーが発生しました: {str(e)}"}


def move_drive_file(file_id, folder_id):
    """Move a file to a specific folder in Google Drive"""
    try:
        creds = get_google_credentials()
        if not creds:
             return {"error": "Google認証に失敗しました。"}
             
        drive_service = build('drive', 'v3', credentials=creds)
        
        # 1. Get current parents
        file = drive_service.files().get(
            fileId=file_id,
            fields='parents',
            supportsAllDrives=True
        ).execute()
        previous_parents = ",".join(file.get('parents', []))
        
        # 2. Add new parent, remove old parents
        file = drive_service.files().update(
            fileId=file_id,
            addParents=folder_id,
            removeParents=previous_parents,
            fields='id, parents',
            supportsAllDrives=True
        ).execute()
        
        return {
            "success": True, 
            "file_id": file.get('id'),
            "message": f"ファイルを移動しました (Folder ID: {folder_id})"
        }
    except Exception as e:
        return {"error": f"ファイル移動中にエラーが発生しました: {str(e)}"}


def rename_file(file_id, new_name):
    """Rename a file or folder in Google Drive"""
    try:
        creds = get_google_credentials()
        if not creds:
             return {"error": "Google認証に失敗しました。"}
             
        drive_service = build('drive', 'v3', credentials=creds)
        
        file = drive_service.files().update(
            fileId=file_id,
            body={'name': new_name},
            fields='id, name, mimeType',
            supportsAllDrives=True
        ).execute()
        
        return {
            "success": True, 
            "id": file.get('id'),
            "name": file.get('name'),
            "message": f"名前を「{file.get('name')}」に変更しました"
        }
    except Exception as e:
        return {"error": f"名前変更中にエラーが発生しました: {str(e)}"}


def search_drive(query, folder_id=None):
    """Search Google Drive for files"""
    try:
        creds = get_google_credentials()
        if not creds:
            return {"error": "Google認証に失敗しました。"}
        
        drive_service = build('drive', 'v3', credentials=creds)
        
        # Escape single quotes in query to prevent syntax errors
        safe_query = query.replace("'", "\\'")
        
        # Query construction
        q_str = f"name contains '{safe_query}' and trashed=false"
        if folder_id:
            q_str += f" and '{folder_id}' in parents"
            
        # Search includes Shared Drives
        # Limit pageSize to 30 to prevent Gemini token exhaustion
        results = drive_service.files().list(
            q=q_str,
            pageSize=30,
            fields="files(id, name, mimeType, webViewLink, modifiedTime)",
            corpora='allDrives',
            includeItemsFromAllDrives=True,
            supportsAllDrives=True
        ).execute()
        
        files = results.get('files', [])
        
        # Enhancement: If result includes a folder, list its contents proactively
        # This solves "Found folder but don't know content"
        try:
            expanded_results = []
            for f in files:
                expanded_results.append(f)
                if f.get('mimeType') == 'application/vnd.google-apps.folder':
                    # List children - restrict to 20 to prevent token explosion
                    children_res = drive_service.files().list(
                        q=f"'{f['id']}' in parents and trashed=false",
                        pageSize=20, 
                        fields="files(id, name, mimeType, webViewLink, modifiedTime)",
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True
                    ).execute()
                    children = children_res.get('files', [])
                    for c in children:
                        c['parent_folder_name'] = f['name']
                        expanded_results.append(c)
            
            # Update files list with expanded content
            if expanded_results:
                files = expanded_results
                
        except Exception as e:
            print(f"Folder expansion error: {e}", file=sys.stderr)
            # Proceed with original results if expansion fails

        return {"success": True, "files": files, "count": len(files)}
    except Exception as e:
        return {"error": f"検索中にエラーが発生しました: {str(e)}"}


def list_gmail(query="is:unread", max_results=5):
    """List Gmail messages matching query"""
    try:
        creds = get_google_credentials()
        if not creds:
            return {"error": "Google認証に失敗しました。"}

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
                    'date': headers.get('Date', ''),
                    'snippet': msg_data.get('snippet', '')
                })
            except Exception as e:
                print(f"Error getting message: {e}", file=sys.stderr)
                continue

        return {"success": True, "emails": email_list, "count": len(email_list)}
    except Exception as e:
        print(f"Gmail error: {e}", file=sys.stderr)
        return {"error": f"Gmail操作中にエラーが発生しました: {str(e)}"}


def list_calendar_events(query=None, time_min=None, time_max=None):
    """List calendar events"""
    try:
        creds = get_google_credentials()
        if not creds:
            return {"error": "Google認証に失敗しました。"}
        
        service = build('calendar', 'v3', credentials=creds)
        
        # Helper to ensure RFC3339 format with Timezone
        def ensure_rfc3339(t_str):
            if not t_str: return None
            if 'T' in t_str and ('+' not in t_str and 'Z' not in t_str[-1]):
                return t_str + '+09:00' # Assume JST if no timezone
            return t_str

        time_min = ensure_rfc3339(time_min)
        time_max = ensure_rfc3339(time_max)
        
        # Default to now (JST) if not specified
        if not time_min:
            import datetime
            # Use JST for "now"
            tz_jst = datetime.timezone(datetime.timedelta(hours=9))
            now = datetime.datetime.now(tz_jst).isoformat()
            time_min = now
            
        events_result = service.events().list(
            calendarId='primary', 
            timeMin=time_min,
            timeMax=time_max,
            q=query,
            maxResults=10, 
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        return {"success": True, "events": events, "count": len(events)}
        
    except Exception as e:
        print(f"Calendar list error: {e}", file=sys.stderr)
        return {"error": f"カレンダー取得中にエラーが発生しました: {str(e)}"}


def create_calendar_event(summary, start_time, end_time=None, location=None):
    """Create a new calendar event"""
    try:
        creds = get_google_credentials()
        if not creds:
            return {"error": "Google認証に失敗しました。"}
        
        service = build('calendar', 'v3', credentials=creds)
        
        event = {
            'summary': summary,
            'location': location,
            'start': {
                'dateTime': start_time,
                'timeZone': 'Asia/Tokyo',
            },
            'end': {
                'dateTime': end_time if end_time else start_time,
                'timeZone': 'Asia/Tokyo',
            },
        }

        event = service.events().insert(calendarId='primary', body=event).execute()
        print(f"Event created: {event.get('htmlLink')}", file=sys.stderr)
        return {"success": True, "event": event, "link": event.get('htmlLink')}
        
    except Exception as e:
        print(f"Calendar create error: {e}", file=sys.stderr)
        return {"error": f"予定の作成中にエラーが発生しました: {str(e)}"}


def find_free_slots(start_date=None, end_date=None, duration_minutes=60, work_start=10, work_end=18):
    """Find free time slots in calendar"""
    try:
        from datetime import datetime, timedelta, timezone
        
        # JST Timezone
        jst = timezone(timedelta(hours=9))
        
        # Default: Search from tomorrow to 7 days ahead
        if not start_date:
            start_date = (datetime.now(jst) + timedelta(days=1)).strftime('%Y-%m-%d')
        if not end_date:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = (start_dt + timedelta(days=7)).strftime('%Y-%m-%d')
            
        # Parse Dates
        dt_start = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=jst)
        dt_end = datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=jst)
        
        # Get existing events
        # Note: We query all events in the range
        existing_revents_res = list_calendar_events(
            time_min=dt_start.isoformat(), 
            time_max=dt_end.isoformat()
        )
        if "error" in existing_revents_res:
             return existing_revents_res
             
        existing_events = existing_revents_res.get('events', [])
        
        # Convert existing events to datetime objects for collision check
        busy_slots = []
        for e in existing_events:
            start = e.get('start', {}).get('dateTime') or e.get('start', {}).get('date')
            end = e.get('end', {}).get('dateTime') or e.get('end', {}).get('date')
            if start and end:
                # Handle full day events (date only) by creating datetime
                if 'T' not in start: 
                    s_dt = datetime.strptime(start, '%Y-%m-%d').replace(tzinfo=jst)
                    e_dt = datetime.strptime(end, '%Y-%m-%d').replace(tzinfo=jst)
                else: 
                     # Parse ISO format (likely contains offset)
                     from dateutil import parser
                     s_dt = parser.parse(start)
                     e_dt = parser.parse(end)
                busy_slots.append((s_dt, e_dt))

        # Scan availability
        available_slots = []
        current_day = dt_start
        
        while current_day <= dt_end:
            # Skip Weekends? (Optional: Making it configurable or assumption-based)
            # For now, include weekends but maybe warn? Let's treat all days equal for now.
            
            # Define working hours for this day
            day_start = current_day.replace(hour=work_start, minute=0, second=0, microsecond=0)
            day_end = current_day.replace(hour=work_end, minute=0, second=0, microsecond=0)
            
            curr = day_start
            while curr + timedelta(minutes=duration_minutes) <= day_end:
                slot_end = curr + timedelta(minutes=duration_minutes)
                
                # Check collision
                is_busy = False
                for b_start, b_end in busy_slots:
                    # Logic: overlapping if (StartA < EndB) and (EndA > StartB)
                    if curr < b_end and slot_end > b_start:
                        is_busy = True
                        break
                
                if not is_busy:
                    # Format neatly
                    available_slots.append(
                        f"{curr.strftime('%m/%d(%a) %H:%M')} - {slot_end.strftime('%H:%M')}"
                    )
                    
                # Move forward (Interval 30 mins to offer flexibility?)
                # Let's move by 60 mins (duration) or shorter interval? 
                # 30 mins step gives more options.
                curr += timedelta(minutes=60) # Simple hourly slots for prompt simplicity
                
                if len(available_slots) >= 10: # Limit result size
                    break
            
            if len(available_slots) >= 10:
                break
            current_day += timedelta(days=1)
            
        if not available_slots:
            return "指定された期間に空き時間は見つかりませんでした。"
            
        return "\n".join(available_slots)
        
    except Exception as e:
        print(f"Free slots check error: {e}", file=sys.stderr)
        return {"error": f"空き時間の検索中にエラーが発生しました: {str(e)}"}


def list_tasks(show_completed=False, due_date=None):
    """List Google Tasks"""
    try:
        creds = get_google_credentials()
        if not creds:
            return {"error": "Google認証に失敗しました。"}
        
        service = build('tasks', 'v1', credentials=creds)
        
        results = service.tasks().list(
            tasklist='@default',
            showCompleted=show_completed,
            maxResults=20
        ).execute()
        
        tasks = results.get('items', [])
        return {"success": True, "tasks": tasks, "count": len(tasks)}
    except Exception as e:
        print(f"Tasks list error: {e}", file=sys.stderr)
        return {"error": f"ToDoリスト取得中にエラーが発生しました: {str(e)}"}


def normalize_to_rfc3339(date_str):
    """
    Convert various date formats to RFC 3339 format for Google Tasks API.
    Accepts: YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS, or already RFC 3339 formatted strings.
    Returns: RFC 3339 formatted string (e.g., 2026-01-30T00:00:00.000Z) or None if invalid.
    """
    if not date_str:
        return None
    
    from datetime import datetime, timezone, timedelta
    
    try:
        # Already in UTC RFC 3339 format
        if date_str.endswith('Z'):
            return date_str
        
        # Already has timezone offset (e.g., +09:00)
        if '+' in date_str or (date_str.count('-') > 2 and 'T' in date_str):
            # Parse and convert to UTC
            if '+' in date_str:
                # Has timezone, parse it
                dt = datetime.fromisoformat(date_str)
                utc_dt = dt.astimezone(timezone.utc)
                return utc_dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        
        # YYYY-MM-DD format (most common from AI)
        if len(date_str) == 10 and date_str.count('-') == 2:
            # Treat as midnight JST, convert to UTC
            jst = timezone(timedelta(hours=9))
            dt = datetime.strptime(date_str, '%Y-%m-%d').replace(hour=0, minute=0, second=0, tzinfo=jst)
            utc_dt = dt.astimezone(timezone.utc)
            return utc_dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        
        # YYYY-MM-DDTHH:MM:SS without timezone
        if 'T' in date_str and len(date_str) >= 19:
            jst = timezone(timedelta(hours=9))
            dt = datetime.fromisoformat(date_str).replace(tzinfo=jst)
            utc_dt = dt.astimezone(timezone.utc)
            return utc_dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        
        # Fallback: return as-is and let API handle it
        return date_str
        
    except Exception as e:
        print(f"Date normalization error for '{date_str}': {e}", file=sys.stderr)
        return None


def add_task(title, due=None):
    """Add a new Google Task. Accepts due date in YYYY-MM-DD or RFC 3339 format."""
    try:
        creds = get_google_credentials()
        if not creds:
            return {"error": "Google認証に失敗しました。"}
        
        service = build('tasks', 'v1', credentials=creds)
        
        task = {
            'title': title
        }
        
        # Convert due date to RFC 3339 format
        if due:
            normalized_due = normalize_to_rfc3339(due)
            if normalized_due:
                task['due'] = normalized_due
                print(f"Tasks add: converted '{due}' -> '{normalized_due}'", file=sys.stderr)
            else:
                print(f"Tasks add: could not normalize date '{due}', skipping due date", file=sys.stderr)
            
        result = service.tasks().insert(tasklist='@default', body=task).execute()
        return {"success": True, "task": result}
    except Exception as e:
        print(f"Tasks add error: {e}", file=sys.stderr)
        return {"error": f"ToDo追加中にエラーが発生しました: {str(e)}"}


def get_gmail_body(message_id: str):
    """Fetch full email body (plain text) for a given Gmail message ID."""
    try:
        creds = get_google_credentials()
        if not creds:
            return {"error": "Google認証に失敗しました。"}
        gmail_service = build('gmail', 'v1', credentials=creds)
        msg = gmail_service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()
        # Extract headers
        headers = {h['name']: h['value'] for h in msg.get('payload', {}).get('headers', [])}
        # Extract plain text body (may be nested parts)
        def get_plain_text(part):
            if part.get('mimeType') == 'text/plain' and 'data' in part.get('body', {}):
                import base64
                return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
            for sub in part.get('parts', []):
                txt = get_plain_text(sub)
                if txt:
                    return txt
            return ''
        body = get_plain_text(msg.get('payload', {}))
        return {
            "success": True,
            "id": message_id,
            "subject": headers.get('Subject', '(件名なし)'),
            "from": headers.get('From', ''),
            "date": headers.get('Date', ''),
            "body": body
        }

    except Exception as e:
        print(f"Gmail body error: {e}", file=sys.stderr)
        return {"error": f"メール本文取得中にエラーが発生しました: {str(e)}"}

def create_gmail_draft(to: str = None, subject: str = None, body: str = "") -> dict:
    """Create a draft email in Gmail.
    
    Args:
        to: Email address of the recipient (optional)
        subject: Email subject (optional)
        body: Email body content (required)
        
    Returns:
        Dictionary with draft ID and status
    """
    try:
        creds = get_google_credentials()
        if not creds:
            return {"error": "Google認証に失敗しました。"}
        
        service = build('gmail', 'v1', credentials=creds)
        
        from email.message import EmailMessage
        import base64
        
        message = EmailMessage()
        message.set_content(body)
        
        if to:
            message['To'] = to
        if subject:
            message['Subject'] = subject
            
        # Encode the message
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {
            'message': {
                'raw': encoded_message
            }
        }
        
        draft = service.users().drafts().create(userId='me', body=create_message).execute()
        
        print(f"Draft created: {draft['id']}", file=sys.stderr)
        return {
            "success": True,
            "id": draft['id'],
            "status": "Draft created successfully",
            "link": f"https://mail.google.com/mail/u/0/#drafts/{draft['message']['id']}"
        }
        
    except Exception as e:
        print(f"Create draft error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return {"error": f"下書き作成中にエラーが発生しました: {str(e)}"}



# Need fast import for fitz, but it might be heavy, so import inside function or at top
import io

def read_drive_file(file_id: str):
    """
    Read content from a Google Drive file (Google Doc, PDF, or Text).
    Returns text content.
    """
    try:
        creds = get_google_credentials()
        if not creds:
            return {"error": "Google認証に失敗しました。"}
        
        drive_service = build('drive', 'v3', credentials=creds)
        
        # 1. Get file metadata
        file = drive_service.files().get(
            fileId=file_id, 
            fields='name, mimeType',
            supportsAllDrives=True
        ).execute()
        mime_type = file.get('mimeType')
        name = file.get('name')
        
        content = ""
        
        if mime_type == 'application/vnd.google-apps.document':
            # Export Google Doc to Text
            request = drive_service.files().export_media(
                fileId=file_id,
                mimeType='text/plain'
            )
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            content = fh.getvalue().decode('utf-8')
            
        elif mime_type == 'application/pdf':
            # Download PDF and extract text
            request = drive_service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            # Extract text using PyMuPDF
            import fitz
            pdf_data = fh.getvalue()
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            for page in doc:
                content += page.get_text() + "\n"
                
        elif mime_type == 'text/plain' or mime_type == 'application/json':
            # Download Text or JSON file
            request = drive_service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            content = fh.getvalue().decode('utf-8')
        
        elif mime_type == 'application/vnd.google-apps.spreadsheet':
            # Google Sheets API を使用してセル内容を取得
            sheets_service = build('sheets', 'v4', credentials=creds)
            
            # シートのメタデータを取得（全シート名取得）
            spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=file_id).execute()
            sheets_list = spreadsheet.get('sheets', [])
            
            all_content = []
            for sheet in sheets_list:
                sheet_name = sheet['properties']['title']
                # 各シートのデータを取得
                try:
                    result = sheets_service.spreadsheets().values().get(
                        spreadsheetId=file_id,
                        range=f"'{sheet_name}'!A:ZZ"  # 広範囲を取得
                    ).execute()
                    values = result.get('values', [])
                    
                    if values:
                        all_content.append(f"=== シート: {sheet_name} ===")
                        for row in values:
                            all_content.append(" | ".join(str(cell) for cell in row))
                except Exception as sheet_err:
                    all_content.append(f"=== シート: {sheet_name} (読み込みエラー: {sheet_err}) ===")
            
            content = "\n".join(all_content)
            
        else:
            return {"error": f"未対応のファイル形式です: {mime_type}"}
            
        return {"success": True, "title": name, "content": content}
        
    except Exception as e:
        print(f"Read Drive file error: {e}", file=sys.stderr)
        return {"error": f"ファイル読み込み中にエラーが発生しました: {str(e)}"}


from googleapiclient.http import MediaIoBaseUpload

def upload_file_to_drive(filename: str, file_data: bytes, mime_type: str = None) -> dict:
    """
    Upload a file (bytes) to the shared Google Drive folder.
    """
    try:
        print(f"upload_file_to_drive: filename={filename}, mime={mime_type}, data_type={type(file_data)}", file=sys.stderr)
        
        if file_data is None:
            return {"error": "アップロードデータが空です (None)"}
            
        if not isinstance(file_data, bytes):
            # Try to encode if it's string (shouldn't happen but defensive)
            if isinstance(file_data, str):
                file_data = file_data.encode('utf-8')
            else:
                 return {"error": f"データの形式が不正です: {type(file_data)}"}

        creds = get_google_credentials()
        if not creds:
             # Try to print why
             print("get_google_credentials returned None", file=sys.stderr)
             return {"error": "Google認証に失敗しました。"}
        
        drive_service = build('drive', 'v3', credentials=creds)
        folder_id = get_shared_folder_id()
        print(f"Target folder: {folder_id}", file=sys.stderr)
        
        file_metadata = {'name': filename}
        if folder_id:
            file_metadata['parents'] = [folder_id]
            
        # Use resumable=True for large files, but for small ones False might be safer if network is flaky?
        # Default True is fine.
        media = MediaIoBaseUpload(io.BytesIO(file_data), mimetype=mime_type, resumable=True)
        
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink',
            supportsAllDrives=True
        ).execute()
        
        return {
            "success": True, 
            "file_id": file.get('id'), 
            "url": file.get('webViewLink'),
            "filename": filename
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Upload error: {e}", file=sys.stderr)
        return {"error": f"アップロード中にエラーが発生しました: {str(e)}"}


def get_latest_uploads(count: int = 5) -> dict:
    """
    Get the most recently uploaded files from the shared Drive folder.
    Useful for referencing files sent via LINE.
    
    Args:
        count: Number of files to retrieve (default 5)
        
    Returns:
        Dictionary with list of recent files
    """
    try:
        creds = get_google_credentials()
        if not creds:
            return {"error": "Google認証に失敗しました。"}
        
        drive_service = build('drive', 'v3', credentials=creds)
        folder_id = get_shared_folder_id()
        
        # Search for files in the shared folder, sorted by creation time
        query = f"'{folder_id}' in parents and trashed = false"
        
        results = drive_service.files().list(
            q=query,
            pageSize=count,
            orderBy='createdTime desc',
            fields='files(id, name, mimeType, createdTime, webViewLink)',
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        
        files = results.get('files', [])
        
        return {
            "success": True,
            "count": len(files),
            "files": [
                {
                    "id": f.get('id'),
                    "name": f.get('name'),
                    "type": f.get('mimeType'),
                    "created": f.get('createdTime'),
                    "url": f.get('webViewLink')
                }
                for f in files
            ]
        }
        
    except Exception as e:
        print(f"Get latest uploads error: {e}", file=sys.stderr)
        return {"error": f"ファイル一覧取得中にエラーが発生しました: {str(e)}"}


def pdf_to_images(pdf_bytes: bytes) -> list:
    """
    Convert PDF pages to PNG images for Gemini Vision analysis.
    
    Args:
        pdf_bytes: PDF file content as bytes
        
    Returns:
        List of tuples: [(image_bytes, mime_type), ...]
    """
    try:
        import fitz  # PyMuPDF
        
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        images = []
        
        # Convert each page (limit to first 3 pages to avoid too much data)
        for page_num in range(min(len(doc), 3)):
            page = doc[page_num]
            # Render at 150 DPI for good quality without being too large
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes("png")
            images.append((img_bytes, "image/png"))
        
        doc.close()
        print(f"PDF converted: {len(images)} pages", file=sys.stderr)
        return images
        
    except ImportError:
        print("PyMuPDF not installed, PDF to image conversion unavailable", file=sys.stderr)
        return []
    except Exception as e:
        print(f"PDF to image conversion error: {e}", file=sys.stderr)
        return []



