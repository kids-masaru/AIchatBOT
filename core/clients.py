"""
Client Registry - Multi-tenant management for AIchatBOT.
Maps client_id to their respective credentials and configuration.
"""
import os
import json

class ClientRegistry:
    def __init__(self, master_config_path="master_config.json"):
        self.master_config_path = master_config_path
        self.error = None
        self.clients = self._load_master_config()

    def _load_master_config(self):
        """Load client configurations from a master JSON file or environment."""
        # 1. Try environment variable (best for Railway/Production)
        master_env = os.environ.get("MASTER_CONFIG")
        if master_env:
            try:
                return json.loads(master_env)
            except Exception as e:
                self.error = f"JSON Error: {str(e)}"
                print(f"Error parsing MASTER_CONFIG env: {e}")

        # 2. Try master_config.json
        if os.path.exists(self.master_config_path):
            with open(self.master_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 3. Fallback to .env values
        return {
            "default": {
                "line_channel_secret": os.environ.get("LINE_CHANNEL_SECRET"),
                "line_channel_access_token": os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"),
                "spreadsheet_id": os.environ.get("SPREADSHEET_ID"),
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
