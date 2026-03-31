"""
Escalation Management
Moraが答えられない質問を井崎さんのLINEに通知し、
回答をクライアントへ転送・知識として蓄積する仕組み。
"""
import os
import sys
import json
import datetime
import urllib.request

ESCALATION_SHEET_ID = os.environ.get("ESCALATION_SHEET_ID")
IZAKI_LINE_USER_ID = os.environ.get("IZAKI_LINE_USER_ID")

# Moraがエスカレーションを示すフレーズ（BASE_SYSTEM_PROMPTの指針3と一致）
ESCALATION_TRIGGER = "井崎に直接ご確認ください"


def should_escalate(response_text: str) -> bool:
    """レスポンステキストにエスカレーションフレーズが含まれるか判定"""
    return ESCALATION_TRIGGER in response_text


def _get_sheet_service():
    try:
        from utils.auth import get_google_credentials
        from googleapiclient.discovery import build
        creds = get_google_credentials()
        if not creds:
            return None
        return build('sheets', 'v4', credentials=creds)
    except Exception as e:
        print(f"Sheet service error: {e}", file=sys.stderr)
        return None


def save_escalation(client_id: str, user_id: str, question: str, mora_response: str) -> str:
    """
    エスカレーションをGoogle Sheetsに保存し、IDを返す。
    ESCALATION_SHEET_IDが未設定の場合はスキップ（ログのみ）。
    """
    jst = datetime.timezone(datetime.timedelta(hours=9))
    now = datetime.datetime.now(jst)
    escalation_id = f"E{now.strftime('%Y%m%d%H%M%S')}"

    if not ESCALATION_SHEET_ID:
        print(f"[Escalation] {escalation_id}: {question[:50]}... (Sheet未設定のため記録スキップ)", file=sys.stderr)
        return escalation_id

    try:
        service = _get_sheet_service()
        if not service:
            return escalation_id

        row = [
            escalation_id,
            now.strftime('%Y-%m-%d %H:%M:%S'),
            client_id,
            user_id,
            question,
            mora_response,
            "pending",
            ""  # 回答欄（空）
        ]
        service.spreadsheets().values().append(
            spreadsheetId=ESCALATION_SHEET_ID,
            range='A:H',
            valueInputOption='RAW',
            body={'values': [row]}
        ).execute()
        print(f"[Escalation] Saved {escalation_id}", file=sys.stderr)
    except Exception as e:
        print(f"[Escalation] Save error: {e}", file=sys.stderr)

    return escalation_id


def notify_izaki(escalation_id: str, client_id: str, question: str) -> bool:
    """
    井崎さんのLINEにエスカレーション通知を送る。
    IZAKI_LINE_USER_IDが未設定の場合はスキップ。
    """
    if not IZAKI_LINE_USER_ID:
        print("[Escalation] IZAKI_LINE_USER_ID未設定のため通知スキップ", file=sys.stderr)
        return False

    try:
        from core.clients import registry
        client_config = registry.get_client('default') or {}
        access_token = (
            client_config.get('line_channel_access_token')
            or os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', '')
        )
        if not access_token:
            print("[Escalation] アクセストークン未設定", file=sys.stderr)
            return False

        message = (
            f"【エスカレーション {escalation_id}】\n"
            f"クライアント: {client_id}\n\n"
            f"質問内容:\n{question}\n\n"
            f"▶ 管理画面から回答: /admin/escalations"
        )
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
        print(f"[Escalation] Notified 井崎さん: {escalation_id}", file=sys.stderr)
        return True
    except Exception as e:
        print(f"[Escalation] Notify error: {e}", file=sys.stderr)
        return False


def save_and_notify(client_id: str, user_id: str, question: str, mora_response: str) -> str:
    """保存と通知をまとめて実行。エスカレーションIDを返す。"""
    escalation_id = save_escalation(client_id, user_id, question, mora_response)
    notify_izaki(escalation_id, client_id, question)
    return escalation_id


def get_pending_escalations() -> list:
    """未回答のエスカレーション一覧を返す。"""
    if not ESCALATION_SHEET_ID:
        return []
    try:
        service = _get_sheet_service()
        if not service:
            return []

        result = service.spreadsheets().values().get(
            spreadsheetId=ESCALATION_SHEET_ID,
            range='A:H'
        ).execute()

        rows = result.get('values', [])
        escalations = []
        for row in rows[1:]:  # 1行目はヘッダー
            if len(row) >= 7 and row[6] == 'pending':
                escalations.append({
                    'id':           row[0] if len(row) > 0 else '',
                    'timestamp':    row[1] if len(row) > 1 else '',
                    'client_id':    row[2] if len(row) > 2 else '',
                    'user_id':      row[3] if len(row) > 3 else '',
                    'question':     row[4] if len(row) > 4 else '',
                    'mora_response': row[5] if len(row) > 5 else '',
                })
        return escalations
    except Exception as e:
        print(f"[Escalation] Get pending error: {e}", file=sys.stderr)
        return []


def resolve_escalation(escalation_id: str, answer: str) -> bool:
    """
    エスカレーションを解決済みにし、元のユーザーに回答を送信する。
    回答はGoogle Driveの知識ソースにも保存できる（オプション）。
    """
    if not ESCALATION_SHEET_ID:
        return False
    try:
        service = _get_sheet_service()
        if not service:
            return False

        result = service.spreadsheets().values().get(
            spreadsheetId=ESCALATION_SHEET_ID,
            range='A:H'
        ).execute()
        rows = result.get('values', [])

        for i, row in enumerate(rows):
            if row and row[0] == escalation_id:
                row_num = i + 1  # 1-indexed
                client_id = row[2] if len(row) > 2 else ''
                user_id = row[3] if len(row) > 3 else ''

                # ステータス・回答を更新
                service.spreadsheets().values().update(
                    spreadsheetId=ESCALATION_SHEET_ID,
                    range=f'G{row_num}:H{row_num}',
                    valueInputOption='RAW',
                    body={'values': [['resolved', answer]]}
                ).execute()

                # 元のユーザーに回答を送信
                if client_id and user_id:
                    _push_answer_to_user(client_id, user_id, answer)

                return True
        return False
    except Exception as e:
        print(f"[Escalation] Resolve error: {e}", file=sys.stderr)
        return False


def _push_answer_to_user(client_id: str, user_id: str, answer: str):
    """解決した回答を元のLINEユーザーへプッシュ送信する。"""
    try:
        from core.clients import registry
        client_config = registry.get_client(client_id) or {}
        access_token = client_config.get('line_channel_access_token', '')
        if not access_token:
            print(f"[Escalation] No token for {client_id}", file=sys.stderr)
            return

        message = f"【井崎より回答】\n{answer}"
        data = json.dumps({
            "to": user_id,
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
        print(f"[Escalation] Answer pushed to {user_id[:8]}", file=sys.stderr)
    except Exception as e:
        print(f"[Escalation] Push answer error: {e}", file=sys.stderr)
