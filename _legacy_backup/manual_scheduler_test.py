from app import app
from tools.google_ops import find_free_slots, list_calendar_events
import json

print("\n--- Testing Calendar Read ---")
try:
    with app.app_context():
        # Check raw events first
        events = list_calendar_events()
        print(f"Current Events: {len(events.get('events', []))}")
        
        print("\n--- Testing Free Slots (Next 7 days) ---")
        slots = find_free_slots()
        print(f"Free Slots Result:\n{slots}")
        
except Exception as e:
    print(f"Test Error: {e}")
