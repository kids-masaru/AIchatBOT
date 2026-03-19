"""
Client Registry - Multi-tenant management for AIchatBOT.
Maps client_id to their respective credentials and configuration.
"""
import os
import json

class ClientRegistry:
    def __init__(self, master_config_path="master_config.json"):
        self.master_config_path = master_config_path
        self.clients = self._load_master_config()

    def _load_master_config(self):
        """Load client configurations from a master JSON file or environment."""
        # For initial testing, we'll try to load from master_config.json
        # If not found, we use the local .env as 'default' client for backward compatibility
        if os.path.exists(self.master_config_path):
            with open(self.master_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Fallback to .env values for a 'default' client
            return {
                "default": {
                    "line_channel_secret": os.environ.get("LINE_CHANNEL_SECRET"),
                    "line_channel_access_token": os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"),
                    "spreadsheet_id": os.environ.get("SPREADSHEET_ID"), # Optional, fallback to creation
                    "knowledge_folder_id": os.environ.get("GOOGLE_DRIVE_FOLDER_ID"),
                    "bot_name": "Koto",
                    "personality": "Helpful Office Assistant"
                }
            }

    def get_client(self, client_id):
        """Retrieve config for a specific client."""
        return self.clients.get(client_id)

    def list_clients(self):
        return list(self.clients.keys())

# Global registry instance
registry = ClientRegistry()
