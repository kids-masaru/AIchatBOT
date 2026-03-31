"""
Inquiry Log & Report Generator (T20)
クライアントごとの問い合わせを記録し、週次・月次レポートを生成する。
"""
import os
import sys
import json
import datetime

INQUIRY_LOG_SHEET_ID = os.environ.get("INQUIRY_LOG_SHEET_ID")


def _get_sheet_service():
    try:
        from utils.auth import get_google_credentials
        from googleapiclient.discovery import build
        creds = get_google_credentials()
        if not creds:
            return None
        return build('sheets', 'v4', credentials=creds)
    except Exception as e:
        print(f"[InquiryLog] Sheet service error: {e}", file=sys.stderr)
        return None


def log_inquiry(client_id: str, user_id: str, question: str, response: str):
    """問い合わせをGoogle Sheetsに記録する。"""
    if not INQUIRY_LOG_SHEET_ID:
        return  # シート未設定時はスキップ

    try:
        jst = datetime.timezone(datetime.timedelta(hours=9))
        now = datetime.datetime.now(jst)
        service = _get_sheet_service()
        if not service:
            return

        row = [
            now.strftime('%Y-%m-%d %H:%M:%S'),
            client_id,
            user_id,
            question[:500],    # 質問（長すぎる場合は切り捨て）
            response[:500],    # 回答
            now.strftime('%Y-%m'),   # 年月（集計用）
            now.strftime('%Y-W%V'),  # 年週（集計用）
        ]
        service.spreadsheets().values().append(
            spreadsheetId=INQUIRY_LOG_SHEET_ID,
            range='A:G',
            valueInputOption='RAW',
            body={'values': [row]}
        ).execute()
    except Exception as e:
        print(f"[InquiryLog] Log error: {e}", file=sys.stderr)


def generate_report(client_id: str = None, period: str = "weekly") -> str:
    """
    問い合わせレポートを生成して返す。
    period: "weekly" (直近7日) or "monthly" (直近30日)
    client_id: 指定すると特定クライアントのみ集計。Noneで全クライアント。
    """
    if not INQUIRY_LOG_SHEET_ID:
        return "INQUIRY_LOG_SHEET_IDが設定されていないためレポートを生成できません。"

    try:
        service = _get_sheet_service()
        if not service:
            return "Google Sheets接続エラー"

        result = service.spreadsheets().values().get(
            spreadsheetId=INQUIRY_LOG_SHEET_ID,
            range='A:G'
        ).execute()
        rows = result.get('values', [])
        if len(rows) <= 1:
            return "記録された問い合わせがまだありません。"

        jst = datetime.timezone(datetime.timedelta(hours=9))
        now = datetime.datetime.now(jst)
        days = 7 if period == "weekly" else 30
        cutoff = now - datetime.timedelta(days=days)

        # 対象期間・クライアントで絞り込み
        filtered = []
        for row in rows[1:]:
            if len(row) < 4:
                continue
            try:
                ts = datetime.datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S').replace(tzinfo=jst)
            except ValueError:
                continue
            if ts < cutoff:
                continue
            if client_id and row[1] != client_id:
                continue
            filtered.append(row)

        if not filtered:
            label = "直近7日間" if period == "weekly" else "直近30日間"
            return f"{label}の問い合わせ記録はありません。"

        # クライアントごとに集計
        from collections import Counter
        client_counts = Counter(row[1] for row in filtered)
        total = len(filtered)

        label = "週次" if period == "weekly" else "月次"
        period_label = "直近7日間" if period == "weekly" else "直近30日間"
        lines = [
            f"【{label}問い合わせレポート】",
            f"集計期間: {period_label}（{cutoff.strftime('%m/%d')} 〜 {now.strftime('%m/%d')}）",
            f"総問い合わせ数: {total}件",
            "",
        ]

        if not client_id:
            lines.append("▼ クライアント別件数")
            for cid, count in client_counts.most_common():
                lines.append(f"  ・{cid}: {count}件")
            lines.append("")

        # よくある質問キーワード（簡易集計）
        words = []
        for row in filtered:
            q = row[3] if len(row) > 3 else ''
            words.extend(q.split())
        word_counts = Counter(w for w in words if len(w) >= 4)  # 4文字以上の単語
        if word_counts:
            lines.append("▼ よく出るキーワード（上位5）")
            for word, count in word_counts.most_common(5):
                lines.append(f"  ・{word}: {count}回")
            lines.append("")

        # エスカレーション件数
        esc_count = sum(1 for row in filtered if len(row) > 4 and "井崎に直接ご確認" in row[4])
        if esc_count:
            lines.append(f"▼ エスカレーション件数: {esc_count}件")

        return "\n".join(lines)

    except Exception as e:
        print(f"[InquiryLog] Report error: {e}", file=sys.stderr)
        return f"レポート生成中にエラーが発生しました。"
