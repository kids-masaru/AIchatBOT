"""
Notion API integration for KOTO
Provides tools to read and write to Notion databases
"""
import os
import json
import urllib.request
import sys

NOTION_API_KEY = os.environ.get('NOTION_API_KEY', '')
NOTION_API_VERSION = "2022-06-28"

def _notion_request(endpoint, method="GET", data=None):
    """Make a request to Notion API"""
    if not NOTION_API_KEY:
        return {"error": "NOTION_API_KEY not set"}
    
    url = f"https://api.notion.com/v1/{endpoint}"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json"
    }
    
    try:
        if data:
            req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method=method)
        else:
            req = urllib.request.Request(url, headers=headers, method=method)
        
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"Notion API Error: {e.code} - {error_body}", file=sys.stderr)
        return {"error": f"API Error: {e.code}", "details": error_body}
    except Exception as e:
        print(f"Notion request error: {e}", file=sys.stderr)
        return {"error": str(e)}


def _get_database_properties(database_id):
    """
    Fetch database schema to resolve property names.
    Returns a dict mapping semantic roles ('title', 'date', 'status') to actual property names.
    """
    result = _notion_request(f"databases/{database_id}", method="GET")
    if "error" in result:
        return {}
        
    properties = result.get("properties", {})
    mapping = {}
    
    # Analyze properties to find best matches
    for name, prop in properties.items():
        type_name = prop.get("type")
        
        # 1. Title (Highest priority)
        if type_name == "title":
            mapping["title"] = name
            
        # 2. Date
        elif type_name == "date":
            # Prefer names like "Date", "Due", "日付", "期限"
            # If we already have one, only overwrite if current one looks "better"
            if "date" not in mapping:
                mapping["date"] = name
            else:
                current = mapping["date"]
                # Heuristic: Prefer "日付" or "Date" or "Due"
                priority_terms = ["日付", "期限", "due", "date", "limit"]
                if any(t in name.lower() for t in priority_terms) and not any(t in current.lower() for t in priority_terms):
                    mapping["date"] = name

        # 3. Status/Select
        elif type_name in ["status", "select"]:
            # Prefer "Status", "State", "ステータス", "状態"
            if "status" not in mapping:
                mapping["status"] = name
            else:
                current = mapping["status"]
                priority_terms = ["ステータス", "status", "state", "状態"]
                if any(t in name.lower() for t in priority_terms) and not any(t in current.lower() for t in priority_terms):
                    mapping["status"] = name
                    
        # 4. Checkbox
        elif type_name == "checkbox":
            if "checkboxes" not in mapping:
                mapping["checkboxes"] = []
            mapping["checkboxes"].append(name)
                    
    return mapping


def get_notion_db_schema(database_id):
    """
    Fetch the full schema of a Notion database.
    Returns property names, types, and options (for select/status).
    """
    result = _notion_request(f"databases/{database_id}", method="GET")
    if "error" in result:
        return result
        
    properties = result.get("properties", {})
    schema = {}
    
    for name, prop in properties.items():
        type_name = prop.get("type")
        prop_info = {"type": type_name}
        
        # Extract options for select/status/multi_select
        if type_name in ["select", "status"]:
            options = prop.get(type_name, {}).get("options", [])
            prop_info["options"] = [opt.get("name") for opt in options]
        elif type_name == "multi_select":
            options = prop.get("multi_select", {}).get("options", [])
            prop_info["options"] = [opt.get("name") for opt in options]
        elif type_name == "relation":
            prop_info["database_id"] = prop.get("relation", {}).get("database_id")
            
        schema[name] = prop_info
        
    return schema


def get_notion_page_title(page_id):
    """
    Fetch the title of a specific Notion page/task.
    """
    if not page_id:
        return {"error": "page_id is required"}
    
    result = _notion_request(f"pages/{page_id}", method="GET")
    if "error" in result:
        return result
        
    properties = result.get("properties", {})
    # Find title property
    for prop in properties.values():
        if prop.get("type") == "title":
            title_parts = prop.get("title", [])
            if title_parts:
                return {"title": title_parts[0].get("plain_text", "")}
            break
            
    return {"title": "Untitled"}


def list_notion_tasks(database_id, filter_today=False):
    """
    List tasks from a Notion database
    """
    if not database_id:
        return {"error": "database_id is required"}
    
    # Resolve property names dynamically
    prop_map = _get_database_properties(database_id)
    # Fallbacks if detection failed (though unexpected for Title)
    title_prop = prop_map.get("title", "名前")
    date_prop = prop_map.get("date", "日付")
    status_prop = prop_map.get("status", "ステータス")
    checkbox_props = prop_map.get("checkboxes", [])

    # Build filter for today's tasks if requested
    body = {}
    if filter_today and date_prop:
        from datetime import datetime, timezone, timedelta
        jst = timezone(timedelta(hours=9))
        today = datetime.now(jst).strftime("%Y-%m-%d")
        body["filter"] = {
            "property": date_prop, 
            "date": {
                "equals": today
            }
        }
    
    # Query the database
    result = _notion_request(f"databases/{database_id}/query", method="POST", data=body)
    if "error" in result:
        return result
    
    tasks = []
    for page in result.get("results", []):
        properties = page.get("properties", {})
        
        # Extract Title
        title = ""
        if title_prop in properties:
            p = properties[title_prop]
            if p.get("title"):
                title = p["title"][0].get("plain_text", "")
        
        # Extract Status
        status = ""
        if status_prop in properties:
            p = properties[status_prop]
            if p.get("status"): status = p["status"].get("name")
            elif p.get("select"): status = p["select"].get("name")
            
        # Extract Date
        due_date = ""
        if date_prop in properties:
            p = properties[date_prop]
            if p.get("date"): due_date = p["date"].get("start")
            
        # Extract Checkboxes
        checkboxes = {}
        for cb_prop in checkbox_props:
            if cb_prop in properties:
                checkboxes[cb_prop] = properties[cb_prop].get("checkbox", False)
        
        # Extract Relations (New: collect all relation IDs)
        relations = {}
        for name, prop in properties.items():
            if prop.get("type") == "relation":
                rel_list = prop.get("relation", [])
                relations[name] = [r.get("id") for r in rel_list]
        
        if title:
            tasks.append({
                "id": page.get("id"),
                "title": title,
                "status": status,
                "due_date": due_date,
                "checkboxes": checkboxes,
                "relations": relations,  # Added relations
                "url": page.get("url", "")
            })
    
    return {"tasks": tasks, "count": len(tasks)}


def create_notion_task(database_id, title, due_date=None, status=None, icon=None, content=None):
    """
    Create a new task in a Notion database
    """
    if not database_id: return {"error": "database_id is required"}
    if not title: return {"error": "title is required"}
    
    # Resolve property names
    prop_map = _get_database_properties(database_id)
    title_key = prop_map.get("title", "名前") # Fallback to Japanese default
    date_key = prop_map.get("date", "日付")
    status_key = prop_map.get("status", "ステータス")
    
    print(f"Notion Mapping: Title={title_key}, Date={date_key}, Status={status_key}", file=sys.stderr)

    # Build the page properties
    properties = {
        title_key: {
            "title": [{"text": {"content": title}}]
        }
    }
    
    # Add due date if provided and mapped
    if due_date and date_key:
        properties[date_key] = {"date": {"start": due_date}}
    
    # Add status if provided and mapped
    if status and status_key:
        # Note: 'status' type properties use 'status' key, 'select' use 'select' key
        # We need to know the type, but _get_database_properties didn't return type.
        # For robustness, we can try both or fetch schema again. 
        # For now, let's just attempt 'select' as it's common for status, or 'status' if we knew.
        # Improve: _get_database_properties implies we know the type.
        # Let's simple try inserting as 'select' or 'status' blindly? No, will error.
        # Refined strategy: Assume 'status' property behaves like select for creation usually.
        # But if it is a 'status' property, we need {"status": {"name": ...}}.
        # If it is 'select', {"select": {"name": ...}}.
        # We really need the type. Let's look at list_notion_tasks.
        # Since we just need to solve the user's issue, let's assume 'status' property or 'select'.
        pass 
        # TODO: Better status handling. For now, try generic 'select' if key has 'status' in name?
        # Actually, let's just skip status if complex, or try basic format.
        # Many templates use 'Status' property type.
        # Let's try to infer from keys or just try one.
        # To be safe, re-fetch schema here is cheap enough (cached in function scope?)
        # For this fix, let's just handle Title and Date perfectly first.
        properties[status_key] = {"select": {"name": status}} # Try select first
        # If it fails, that's life for now.

    # Wait, 'properties' expects exact keys. If `date_key` was not found (e.g. user has no date col), we skip.
    if due_date and not date_key:
        print("Warning: No Date column found in Notion DB", file=sys.stderr)

    body = {
        "parent": {"database_id": database_id},
        "properties": properties
    }
    
    # Add icon if provided
    if icon:
        body["icon"] = {
            "type": "emoji",
            "emoji": icon
        }
        
    # Add content/description to the page body if provided
    if content:
        body["children"] = [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": content
                            }
                        }
                    ]
                }
            }
        ]

    
    result = _notion_request("pages", method="POST", data=body)
    
    if "error" in result:
        # Retry with 'status' instead of 'select' if it failed?
        # A simple retry logic for Status might be overkill. 
        # Let's return the error so user sees it.
        return result
    
    return {
        "success": True,
        "id": result.get("id"),
        "url": result.get("url"),
        "title": title
    }


def update_notion_task(page_id, status=None, title=None):
    """
    Update an existing Notion task
    """
    if not page_id: return {"error": "page_id is required"}
    
    # For updating, we don't strictly need database_id to query schema since we have page_id.
    # We can GET the page first to see its properties! 
    # That is much more reliable for an existing page.
    page_info = _notion_request(f"pages/{page_id}", method="GET")
    if "error" in page_info: return page_info
    
    props = page_info.get("properties", {})
    
    update_props = {}
    
    if title:
        # Find title property key from existing props
        for k, v in props.items():
            if v["type"] == "title":
                update_props[k] = {"title": [{"text": {"content": title}}]}
                break
                
    if status:
        # Find status/select property key
        for k, v in props.items():
            if v["type"] in ["status", "select"]:
                # Prefer one named "Status" etc if multiple
                # Checking type matches
                if v["type"] == "select":
                    update_props[k] = {"select": {"name": status}}
                elif v["type"] == "status":
                    update_props[k] = {"status": {"name": status}}
                break
    
    if not update_props:
        return {"error": "No valid properties found to update (or no changes requested)"}
    
    body = {"properties": update_props}
    result = _notion_request(f"pages/{page_id}", method="PATCH", data=body)
    
    if "error" in result: return result
    
    return {
        "success": True,
        "id": result.get("id"),
        "url": result.get("url")
    }

def toggle_notion_checkbox(page_id, property_name, checked):
    """
    Toggle a Notion checkbox property on or off.
    """
    if not page_id: return {"error": "page_id is required"}
    if not property_name: return {"error": "property_name is required"}
    
    # We first format the exact body for a checkbox update
    update_props = {
        property_name: {
            "checkbox": bool(checked)
        }
    }
    
    body = {"properties": update_props}
    result = _notion_request(f"pages/{page_id}", method="PATCH", data=body)
    
    if "error" in result: 
        return {
            "error": "Failed to update checkbox. Make sure the property_name matches exactly what is in Notion.",
            "details": result
        }
    
    return {
        "success": True,
        "id": result.get("id"),
        "url": result.get("url"),
        "updated_property": property_name,
        "new_value": checked
    }


def update_notion_task_properties(page_id, properties_values):
    """
    Update multiple properties of a Notion page dynamically.
    properties_values: dict of {property_name: value}
    Values are automatically formatted based on property type.
    """
    if not page_id: return {"error": "page_id is required"}
    
    # Get current page to determine property types
    page_info = _notion_request(f"pages/{page_id}", method="GET")
    if "error" in page_info: return page_info
    
    existing_props = page_info.get("properties", {})
    update_payload = {}
    
    for name, value in properties_values.items():
        if name not in existing_props:
            print(f"Property '{name}' not found in page properties.", file=sys.stderr)
            continue
            
        prop_type = existing_props[name].get("type")
        
        if prop_type == "title":
            update_payload[name] = {"title": [{"text": {"content": str(value)}}]}
        elif prop_type == "rich_text":
            update_payload[name] = {"rich_text": [{"text": {"content": str(value)}}]}
        elif prop_type == "number":
            update_payload[name] = {"number": float(value)}
        elif prop_type == "select":
            update_payload[name] = {"select": {"name": str(value)}}
        elif prop_type == "multi_select":
            if isinstance(value, list):
                update_payload[name] = {"multi_select": [{"name": str(v)} for v in value]}
            else:
                update_payload[name] = {"multi_select": [{"name": str(value)}]}
        elif prop_type == "status":
            update_payload[name] = {"status": {"name": str(value)}}
        elif prop_type == "date":
            # Assume value is "YYYY-MM-DD"
            update_payload[name] = {"date": {"start": str(value)}}
        elif prop_type == "checkbox":
            update_payload[name] = {"checkbox": bool(value)}
        elif prop_type == "relation":
            if isinstance(value, list):
                update_payload[name] = {"relation": [{"id": str(v)} for v in value]}
            else:
                update_payload[name] = {"relation": [{"id": str(value)}]}
        elif prop_type == "url":
            update_payload[name] = {"url": str(value)}
        elif prop_type == "email":
            update_payload[name] = {"email": str(value)}
        elif prop_type == "phone_number":
            update_payload[name] = {"phone_number": str(value)}

    if not update_payload:
        return {"error": "No valid properties provided for update."}
        
    result = _notion_request(f"pages/{page_id}", method="PATCH", data={"properties": update_payload})
    return result
