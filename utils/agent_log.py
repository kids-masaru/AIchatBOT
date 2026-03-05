"""
Agent Activity Log - In-memory ring buffer for tool execution logs.
Used for LINE debug mode and Dashboard log viewer.
"""
import sys
import json
import datetime
from collections import deque

# Ring buffer: keep last 50 log entries globally
_global_logs = deque(maxlen=50)

# Per-user session logs (for LINE debug mode)
_session_logs = {}  # user_id -> list of log entries

# Debug mode toggle per user
_debug_mode = {}  # user_id -> bool


def is_debug_mode(user_id):
    """Check if debug mode is ON for a user."""
    return _debug_mode.get(user_id, False)


def set_debug_mode(user_id, enabled):
    """Toggle debug mode for a user."""
    _debug_mode[user_id] = enabled
    if enabled:
        _session_logs[user_id] = []
    print(f"[AgentLog] Debug mode {'ON' if enabled else 'OFF'} for {user_id[:8]}", file=sys.stderr)


def add_log(user_id, tool_name, args, result, round_num=0):
    """Record a tool execution log entry."""
    jst = datetime.timezone(datetime.timedelta(hours=9))
    
    # Summarize args (truncate long values)
    args_summary = {}
    for k, v in (args or {}).items():
        v_str = str(v)
        args_summary[k] = v_str[:100] + "..." if len(v_str) > 100 else v_str

    # Summarize result
    if isinstance(result, dict):
        result_str = json.dumps(result, ensure_ascii=False, default=str)
    else:
        result_str = str(result)
    result_summary = result_str[:300] + "..." if len(result_str) > 300 else result_str

    entry = {
        "timestamp": datetime.datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S"),
        "user_id": user_id[:8] if user_id else "unknown",
        "tool_name": tool_name,
        "args_summary": args_summary,
        "result_summary": result_summary,
        "round": round_num
    }

    # Add to global ring buffer
    _global_logs.append(entry)

    # Add to session if debug mode is on
    if is_debug_mode(user_id):
        if user_id not in _session_logs:
            _session_logs[user_id] = []
        _session_logs[user_id].append(entry)


def get_logs(limit=20):
    """Get recent global logs (for dashboard API)."""
    logs = list(_global_logs)
    logs.reverse()  # Newest first
    return logs[:limit]


def get_session_logs(user_id):
    """Get logs for current debug session (for LINE)."""
    return _session_logs.get(user_id, [])


def clear_session(user_id):
    """Clear session logs after sending."""
    _session_logs[user_id] = []


def format_log_for_line(entry):
    """Format a single log entry for LINE message display."""
    tool = entry["tool_name"]
    args = entry.get("args_summary", {})
    result = entry.get("result_summary", "")
    
    # Friendly tool name mapping
    friendly = {
        "consult_fumi": "📝 Fumi (作成)",
        "consult_aki": "📚 Aki (検索)",
        "consult_toki": "📜 Toki (履歴)",
        "consult_ren": "📣 Ren (広報)",
        "consult_rina": "📅 Rina (予定)",
        "get_notion_tasks": "📋 Notion取得",
        "add_notion_task": "➕ Notionタスク追加",
        "google_web_search": "🔍 Web検索",
        "create_google_doc": "📄 Doc作成",
        "calculate": "🧮 計算",
    }
    
    name = friendly.get(tool, f"🔧 {tool}")
    
    # Build message
    args_text = ""
    if args:
        args_items = [f"  {k}: {v}" for k, v in args.items()]
        args_text = "\n".join(args_items[:3])  # Max 3 args shown
    
    # Truncate result for LINE
    result_short = result[:150] + "..." if len(result) > 150 else result
    
    msg = f"{name}\n"
    if args_text:
        msg += f"📥 引数:\n{args_text}\n"
    msg += f"📤 結果: {result_short}"
    
    return msg
