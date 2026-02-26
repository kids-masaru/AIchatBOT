"""
Message Queue System for LINE Webhooks
Handles concurrent requests safely by queuing messages per user
and processing them sequentially to avoid AI confusion.
"""
import os
import sys
import json
import threading
import time
from pathlib import Path
from collections import defaultdict

# Use a local JSON file for persistent queuing
DATA_DIR = Path(__file__).parent.parent / "data"
QUEUE_FILE = DATA_DIR / "webhook_queue.json"

# In-memory lock for thread-safe operations
_queue_lock = threading.Lock()
# Dictionary to track if a worker thread is running for a specific user
_user_workers = {}
_worker_lock = threading.Lock()

# Deduplication: track message IDs for the last few minutes
_processed_messages = set()
_processed_lock = threading.Lock()

def _ensure_data_dir():
    DATA_DIR.mkdir(exist_ok=True)

def _load_queue():
    if not QUEUE_FILE.exists():
        return defaultdict(list)
    try:
        with open(QUEUE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return defaultdict(list, data)
    except Exception as e:
        print(f"Error loading queue: {e}", file=sys.stderr)
        return defaultdict(list)

def _save_queue(queue_data):
    _ensure_data_dir()
    try:
        with open(QUEUE_FILE, 'w', encoding='utf-8') as f:
            json.dump(dict(queue_data), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving queue: {e}", file=sys.stderr)

def enqueue_message(user_id, task_data):
    """
    Add a new message/file task to the user's queue.
    task_data should be a dict containing task details (text, file info, etc.)
    """
    message_id = task_data.get('message_id')
    
    if message_id:
        with _processed_lock:
            if message_id in _processed_messages:
                print(f"[Queue] Skipping duplicate message_id: {message_id}", file=sys.stderr)
                return False
            _processed_messages.add(message_id)
            # Keep the set size manageable (rough cleanup)
            if len(_processed_messages) > 1000:
                _processed_messages.clear()
                
    with _queue_lock:
        queue = _load_queue()
        queue[user_id].append(task_data)
        _save_queue(queue)
    
    # Start a worker thread for this user if one isn't already running
    _start_worker_if_needed(user_id)
    return True

def _start_worker_if_needed(user_id):
    with _worker_lock:
        if user_id not in _user_workers or not _user_workers[user_id].is_alive():
            # Pass the function to be processed. We will define a callback in app.py
            # But to avoid circular imports, we'll let app.py call a start_worker function
            pass

def process_queue_for_user(user_id, process_callback):
    """
    Background worker function that runs until the queue for the user is empty.
    process_callback is the function that actually calls Gemini (e.g., process_message_async)
    """
    def worker_loop():
        print(f"[Queue Worker] Started for user {user_id[:8]}", file=sys.stderr)
        
        # Debounce/Wait briefly to allow concurrent identical-time uploads to queue up
        # We wait 3 seconds before starting the loop to naturally batch immediate follow-ups
        time.sleep(3)
        
        while True:
            tasks_to_process = []
            with _queue_lock:
                queue = _load_queue()
                if user_id in queue and queue[user_id]:
                    # Take all pending tasks at once to batch them
                    tasks_to_process = queue[user_id]
                    # Clear them from the queue
                    queue[user_id] = []
                    _save_queue(queue)
            
            if not tasks_to_process:
                break # Queue empty, worker dies
                
            try:
                # Combine multiple tasks into one context if needed
                print(f"[Queue Worker] Processing {len(tasks_to_process)} batched tasks for {user_id[:8]}", file=sys.stderr)
                process_callback(user_id, tasks_to_process)
            except Exception as e:
                print(f"[Queue Worker] Error processing callback: {e}", file=sys.stderr)
            
            # Briefly sleep before checking queue again
            time.sleep(1)
            
        print(f"[Queue Worker] Stopped for user {user_id[:8]} (Queue empty)", file=sys.stderr)
        
        with _worker_lock:
            if user_id in _user_workers:
                del _user_workers[user_id]

    # Start the thread safely
    with _worker_lock:
        if user_id not in _user_workers or not _user_workers[user_id].is_alive():
            t = threading.Thread(target=worker_loop, daemon=True)
            _user_workers[user_id] = t
            t.start()
