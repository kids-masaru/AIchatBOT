"""
Meeting Minutes Generator (T22)
Google Meetの文字起こしをDriveフォルダから検出し、
議事録を自動生成してLINEで送信する。
"""
import os
import sys
import json
import datetime

MEET_TRANSCRIPT_FOLDER_ID = os.environ.get("MEET_TRANSCRIPT_FOLDER_ID")
MEET_PROCESSED_SHEET_ID = os.environ.get("MEET_PROCESSED_SHEET_ID")  # 処理済みファイルID管理用


def _get_drive_service():
    try:
        from utils.auth import get_google_credentials
        from googleapiclient.discovery import build
        creds = get_google_credentials()
        if not creds:
            return None
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"[MeetMinutes] Drive service error: {e}", file=sys.stderr)
        return None


def _get_processed_file_ids() -> set:
    """処理済みファイルIDをGoogle Sheetsから取得する。"""
    if not MEET_PROCESSED_SHEET_ID:
        return set()
    try:
        from utils.auth import get_google_credentials
        from googleapiclient.discovery import build
        creds = get_google_credentials()
        if not creds:
            return set()
        service = build('sheets', 'v4', credentials=creds)
        result = service.spreadsheets().values().get(
            spreadsheetId=MEET_PROCESSED_SHEET_ID,
            range='A:A'
        ).execute()
        return {row[0] for row in result.get('values', []) if row}
    except Exception as e:
        print(f"[MeetMinutes] Get processed IDs error: {e}", file=sys.stderr)
        return set()


def _mark_as_processed(file_id: str):
    """ファイルIDを処理済みとしてGoogle Sheetsに記録する。"""
    if not MEET_PROCESSED_SHEET_ID:
        return
    try:
        from utils.auth import get_google_credentials
        from googleapiclient.discovery import build
        creds = get_google_credentials()
        if not creds:
            return
        service = build('sheets', 'v4', credentials=creds)
        jst = datetime.timezone(datetime.timedelta(hours=9))
        now = datetime.datetime.now(jst).strftime('%Y-%m-%d %H:%M:%S')
        service.spreadsheets().values().append(
            spreadsheetId=MEET_PROCESSED_SHEET_ID,
            range='A:B',
            valueInputOption='RAW',
            body={'values': [[file_id, now]]}
        ).execute()
    except Exception as e:
        print(f"[MeetMinutes] Mark processed error: {e}", file=sys.stderr)


def get_new_transcripts() -> list:
    """
    MEET_TRANSCRIPT_FOLDER_IDのフォルダ内から未処理の文字起こしファイルを取得する。
    Returns: [{"id": ..., "name": ..., "content": ...}, ...]
    """
    if not MEET_TRANSCRIPT_FOLDER_ID:
        return []

    drive_service = _get_drive_service()
    if not drive_service:
        return []

    try:
        # フォルダ内のGoogleドキュメントを取得（新しい順）
        result = drive_service.files().list(
            q=f"'{MEET_TRANSCRIPT_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.document' and trashed=false",
            orderBy='createdTime desc',
            fields='files(id, name, createdTime)',
            pageSize=10
        ).execute()
        files = result.get('files', [])

        processed_ids = _get_processed_file_ids()
        new_files = [f for f in files if f['id'] not in processed_ids]

        transcripts = []
        for f in new_files[:3]:  # 一度に最大3件処理
            content = _read_doc_content(drive_service, f['id'])
            if content:
                transcripts.append({
                    'id': f['id'],
                    'name': f['name'],
                    'content': content,
                    'created': f.get('createdTime', '')
                })
        return transcripts
    except Exception as e:
        print(f"[MeetMinutes] Get transcripts error: {e}", file=sys.stderr)
        return []


def _read_doc_content(drive_service, file_id: str) -> str:
    """GoogleドキュメントのテキストをExport APIで取得する。"""
    try:
        content = drive_service.files().export(
            fileId=file_id,
            mimeType='text/plain'
        ).execute()
        if isinstance(content, bytes):
            return content.decode('utf-8')
        return str(content)
    except Exception as e:
        print(f"[MeetMinutes] Read doc error: {e}", file=sys.stderr)
        return ""


def generate_minutes(transcript_content: str, file_name: str) -> str:
    """
    Geminiを使って文字起こしから議事録を生成する。
    """
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_api_key:
        return f"【議事録】{file_name}\n\n（Gemini APIキー未設定のため自動生成できませんでした）"

    try:
        from google import genai
        client = genai.Client(api_key=gemini_api_key)

        prompt = f"""以下はGoogle Meetの会議文字起こしです。
これを読んで、簡潔な議事録を日本語で作成してください。

【出力フォーマット】
■ 日時・ファイル名: {file_name}
■ 参加者: （文字起こしから読み取れる場合）
■ 議題・話し合った内容:
  1. （要点を箇条書き）
■ 決定事項:
  - （あれば）
■ 次回アクション:
  - 担当者: タスク内容（あれば）

【文字起こし】
{transcript_content[:8000]}
"""
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )
        return response.text if response.text else "議事録の生成に失敗しました。"
    except Exception as e:
        print(f"[MeetMinutes] Generate error: {e}", file=sys.stderr)
        return f"議事録生成エラー: 文字起こしは受信しましたが処理できませんでした。"


def process_new_transcripts(notify_line_user_id: str = None, access_token: str = None) -> list:
    """
    新しい文字起こしを検出 → 議事録生成 → LINE送信 → 処理済み記録。
    Returns: 処理したファイル名リスト
    """
    transcripts = get_new_transcripts()
    if not transcripts:
        print("[MeetMinutes] No new transcripts found.", file=sys.stderr)
        return []

    processed = []
    for t in transcripts:
        print(f"[MeetMinutes] Processing: {t['name']}", file=sys.stderr)
        minutes = generate_minutes(t['content'], t['name'])

        # LINEで送信
        if notify_line_user_id and access_token:
            _push_minutes(notify_line_user_id, access_token, minutes)

        # 処理済みとして記録
        _mark_as_processed(t['id'])
        processed.append(t['name'])

    return processed


def _push_minutes(user_id: str, access_token: str, minutes_text: str):
    """議事録をLINEにプッシュ送信する（4500文字を超える場合は分割）"""
    import urllib.request
    chunks = [minutes_text[i:i+4000] for i in range(0, len(minutes_text), 4000)]
    for chunk in chunks:
        try:
            data = json.dumps({
                "to": user_id,
                "messages": [{"type": "text", "text": chunk}]
            }).encode('utf-8')
            req = urllib.request.Request(
                'https://api.line.me/v2/bot/message/push',
                data=data,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {access_token}'
                },
                method='POST'
            )
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:
            print(f"[MeetMinutes] Push error: {e}", file=sys.stderr)
