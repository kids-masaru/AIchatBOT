"""
Feedback System (T21)
井崎さんが Mora の回答に ○/× を付けてフィードバックし、
知識として蓄積することで回答精度を高める仕組み。
"""
import os
import sys
import json
import datetime

FEEDBACK_SHEET_ID = os.environ.get("FEEDBACK_SHEET_ID")
IZAKI_LINE_USER_ID = os.environ.get("IZAKI_LINE_USER_ID")


def _get_sheet_service():
    try:
        from utils.auth import get_google_credentials
        from googleapiclient.discovery import build
        creds = get_google_credentials()
        if not creds:
            return None
        return build('sheets', 'v4', credentials=creds)
    except Exception as e:
        print(f"[Feedback] Sheet service error: {e}", file=sys.stderr)
        return None


def save_response_for_feedback(client_id: str, user_id: str, question: str, response: str) -> str:
    """
    フィードバック待ちの回答をGoogle Sheetsに保存し、フィードバックIDを返す。
    全件保存は重いので、エスカレーション済みまたは長文回答のみを対象とする。
    """
    if not FEEDBACK_SHEET_ID:
        return ""

    try:
        jst = datetime.timezone(datetime.timedelta(hours=9))
        now = datetime.datetime.now(jst)
        feedback_id = f"F{now.strftime('%Y%m%d%H%M%S')}"

        service = _get_sheet_service()
        if not service:
            return ""

        row = [
            feedback_id,
            now.strftime('%Y-%m-%d %H:%M:%S'),
            client_id,
            user_id,
            question[:500],
            response[:500],
            "",   # 評価欄（○ or ×）
            "",   # コメント欄
        ]
        service.spreadsheets().values().append(
            spreadsheetId=FEEDBACK_SHEET_ID,
            range='A:H',
            valueInputOption='RAW',
            body={'values': [row]}
        ).execute()
        return feedback_id
    except Exception as e:
        print(f"[Feedback] Save error: {e}", file=sys.stderr)
        return ""


def notify_feedback_request(feedback_id: str, question: str, response: str) -> bool:
    """
    井崎さんのLINEにフィードバック依頼を送る。
    QuickReplyは使えないので、○/×をテキストで返信してもらう形式。
    """
    if not IZAKI_LINE_USER_ID:
        return False

    try:
        from core.clients import registry
        default_config = registry.get_client('default') or {}
        access_token = (
            default_config.get('line_channel_access_token')
            or os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', '')
        )
        if not access_token:
            return False

        message = (
            f"【フィードバック依頼 {feedback_id}】\n\n"
            f"質問:\n{question[:200]}\n\n"
            f"Moraの回答:\n{response[:200]}\n\n"
            f"この回答は井崎さんらしいですか？\n"
            f"・○ → 「{feedback_id} ○」と返信\n"
            f"・× + 修正 → 「{feedback_id} × 正しくはこうです...」と返信"
        )
        import urllib.request
        data = json.dumps({
            "to": IZAKI_LINE_USER_ID,
            "messages": [{"type": "text", "text": message}]
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
        return True
    except Exception as e:
        print(f"[Feedback] Notify error: {e}", file=sys.stderr)
        return False


def record_feedback(feedback_id: str, rating: str, comment: str = "") -> bool:
    """
    フィードバック（○/×）をGoogle Sheetsに記録する。
    rating: "○" or "×"
    comment: 修正コメント（×の場合）
    """
    if not FEEDBACK_SHEET_ID:
        return False

    try:
        service = _get_sheet_service()
        if not service:
            return False

        result = service.spreadsheets().values().get(
            spreadsheetId=FEEDBACK_SHEET_ID,
            range='A:H'
        ).execute()
        rows = result.get('values', [])

        for i, row in enumerate(rows):
            if row and row[0] == feedback_id:
                row_num = i + 1
                service.spreadsheets().values().update(
                    spreadsheetId=FEEDBACK_SHEET_ID,
                    range=f'G{row_num}:H{row_num}',
                    valueInputOption='RAW',
                    body={'values': [[rating, comment]]}
                ).execute()
                print(f"[Feedback] Recorded {feedback_id}: {rating}", file=sys.stderr)
                return True
        return False
    except Exception as e:
        print(f"[Feedback] Record error: {e}", file=sys.stderr)
        return False


def parse_feedback_reply(text: str) -> tuple:
    """
    LINEから返ってきたフィードバック返信をパースする。
    例: "F20260401123456 ○"
        "F20260401123456 × 正しくはこうです..."
    Returns: (feedback_id, rating, comment) or ("", "", "")
    """
    parts = text.strip().split(' ', 2)
    if len(parts) >= 2 and parts[0].startswith('F') and parts[1] in ('○', '×'):
        feedback_id = parts[0]
        rating = parts[1]
        comment = parts[2] if len(parts) > 2 else ""
        return feedback_id, rating, comment
    return "", "", ""
