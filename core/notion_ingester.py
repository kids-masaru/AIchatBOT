"""
Automated Notion Ingestion Module
Fetches updates from specific Notion databases daily and saves them to Pinecone as system memory.
"""
import os
import sys
import json
import traceback
from datetime import datetime, timezone, timedelta
from typing import List, Dict
import requests
from dotenv import load_dotenv

load_dotenv()
NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "")

def get_recent_notion_updates(database_id: str, hours_back: int = 24) -> List[Dict]:
    """
    Fetch Notion database items updated within the last X hours.
    Uses the exact same parsing rules as Nono's notion_analyst/notion_ops.
    """
    if not NOTION_API_KEY:
        print("Notion Ingester: NOTION_API_KEY not found.", file=sys.stderr)
        return []
        
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    # Calculate cutoff time in ISO 8601
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours_back)
    cutoff_iso = cutoff.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    payload = {
        "filter": {
            "timestamp": "last_edited_time",
            "last_edited_time": {
                "after": cutoff_iso
            }
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        
        if response.status_code != 200:
            print(f"Notion API Error [{response.status_code}]: {response.text}", file=sys.stderr)
            return []

        data = response.json()
        results = data.get("results", [])
        
        parsed_items = []
        for row in results:
            page_id = row.get("id", "")
            props = row.get("properties", {})
            page_url = row.get("url", "")
            
            parsed = {}
            for prop_name, prop_data in props.items():
                ptype = prop_data.get('type')
                
                if ptype == 'title':
                    title_arr = prop_data.get('title', [])
                    text = "".join([t.get('plain_text', '') for t in title_arr])
                    parsed['title'] = text
                elif ptype == 'rich_text':
                    text_arr = prop_data.get('rich_text', [])
                    text = "".join([t.get('plain_text', '') for t in text_arr])
                    parsed[prop_name] = text
                elif ptype == 'select':
                    sel = prop_data.get('select')
                    parsed[prop_name] = sel.get('name') if sel else None
                elif ptype == 'multi_select':
                    sels = prop_data.get('multi_select', [])
                    parsed[prop_name] = [s.get('name') for s in sels]
                elif ptype == 'status':
                    status_obj = prop_data.get('status')
                    parsed[prop_name] = status_obj.get('name') if status_obj else None
                elif ptype == 'date':
                    date_obj = prop_data.get('date')
                    if date_obj:
                        start = date_obj.get('start', '')
                        parsed[prop_name] = start
                    else:
                        parsed[prop_name] = None
                elif ptype == 'checkbox':
                    parsed[prop_name] = prop_data.get('checkbox', False)
                elif ptype == 'number':
                    parsed[prop_name] = prop_data.get('number', None)
                elif ptype == 'url':
                    parsed[prop_name] = prop_data.get('url', None)

            # Keep trace of ID
            parsed['page_id'] = f"[{page_id}](Notion_ID)"
            parsed['page_url'] = page_url
            
            parsed_items.append(parsed)
            
        return parsed_items
        
    except Exception as e:
        print(f"Notion Ingester Error: {traceback.format_exc()}", file=sys.stderr)
        return []

def format_notion_updates_for_memory(updates: List[Dict], db_id: str) -> str:
    """Format the list of dictionaries into a readable string for the AI's Brain/RAG."""
    if not updates:
        return ""
        
    lines = []
    lines.append(f"【システム通知: Notionデータベース連携 ({db_id})】")
    lines.append("以下の内容が新しく追加・更新されました：")
    
    for item in updates:
        title = item.get('title', '無題の項目')
        lines.append(f"■ {title}")
        for k, v in item.items():
            if k not in ['title', 'page_id', 'page_url'] and v:
                lines.append(f"  - {k}: {v}")
    
    return "\n".join(lines)

def run_daily_notion_ingestion(user_id: str):
    """
    Called by cron_job in app.py exactly once a day (e.g. at 3 AM).
    Fetches the hardcoded DBs and saves to Pinecone if changes exist.
    """
    print(f"Notion Ingester: Starting daily ingestion for user {user_id[:8]}...", file=sys.stderr)
    
    # User requested these two databases
    TARGET_DBS = [
        "1472359570078062b9fae9595195f565", 
        "313235957007805e9c97ce0a08c10f99"
    ]
    
    from utils.vector_store import save_conversation
    
    total_updates = 0
    
    for db_id in TARGET_DBS:
        # Check last 24 hours (with some overlap safety margin, so 25h)
        updates = get_recent_notion_updates(db_id, hours_back=25)
        
        if updates:
            print(f"Notion Ingester: Found {len(updates)} updates in DB {db_id}.", file=sys.stderr)
            total_updates += len(updates)
            
            formatted_text = format_notion_updates_for_memory(updates, db_id)
            
            # Save to RAG using 'system' role
            # Pinecone will embed this full chunk, making it searchable by topic/title
            metadata_info = {"sub_type": "notion_update", "source_db": db_id}
            
            success = save_conversation(user_id, "system", formatted_text, metadata=metadata_info)
            if not success:
                 print(f"Notion Ingester: Failed to save updates for DB {db_id} to Vector Store.", file=sys.stderr)
        else:
            print(f"Notion Ingester: No recent updates in DB {db_id}.", file=sys.stderr)
            
    print(f"Notion Ingester: Completed. Recorded {total_updates} total updates to memory.", file=sys.stderr)
    return total_updates

if __name__ == "__main__":
    # Local quick test
    db1 = "1472359570078062b9fae9595195f565"
    updates = get_recent_notion_updates(db1, hours_back=24)
    print(json.dumps(updates, indent=2, ensure_ascii=False))
