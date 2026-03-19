
import sys
import os
import json

# Setup
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from core.clients import registry

def test_registry():
    print("--- Testing Client Registry ---")
    clients = registry.list_clients()
    print(f"Registered clients: {clients}")
    
    for client_id in clients:
        config = registry.get_client(client_id)
        print(f"Config for '{client_id}': BotName={config.get('bot_name')}, Spreadsheet={config.get('spreadsheet_id', 'Default')}")
    
    # Test unknown client
    unknown = registry.get_client("non_existent")
    if unknown is None:
        print("Fallback for unknown client works (returns None).")
    else:
        print("Fallback for unknown client FAILED (should be None or default).")

if __name__ == "__main__":
    test_registry()
