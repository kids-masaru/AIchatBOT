"""
Client Registry - Multi-tenant management for AIchatBOT.
Maps client_id to their respective credentials and configuration.
"""
import os
import json

class ClientRegistry:
    def __init__(self, master_config_path="master_config.json"):
        self.master_config_path = master_config_path
        self.registry_sheet_id = os.environ.get("MASTER_REGISTRY_SHEET_ID")
        self.error = None
        self._cache = None
        self._last_load_time = 0
        self._cache_ttl = 300  # 5 minutes
        self.clients = self.load_registry()

    def load_registry(self):
        """Load client configurations from Sheet, Env, or File."""
        import time
        now = time.time()
        
        # Return cache if valid
        if self._cache and (now - self._last_load_time < self._cache_ttl):
            return self._cache

        # 1. Try Google Sheet Registry (Dynamic)
        if self.registry_sheet_id:
            try:
                sheet_clients = self._load_from_sheet(self.registry_sheet_id)
                if sheet_clients:
                    self._cache = sheet_clients
                    self._last_load_time = now
                    self.error = None
                    print(f"Loaded {len(sheet_clients)} clients from Google Sheet Registry.")
                    return sheet_clients
            except Exception as e:
                self.error = f"Sheet Registry Error: {str(e)}"
                print(f"Error loading registry from sheet: {e}")

        # 2. Try environment variable (MASTER_CONFIG)
        master_env = os.environ.get("MASTER_CONFIG")
        if master_env:
            try:
                env_clients = json.loads(master_env)
                self._cache = env_clients
                self._last_load_time = now
                return env_clients
            except Exception as e:
                self.error = f"JSON Error: {str(e)}"
                print(f"Error parsing MASTER_CONFIG env: {e}")

        # 3. Try master_config.json
        if os.path.exists(self.master_config_path):
            with open(self.master_config_path, 'r', encoding='utf-8') as f:
                file_clients = json.load(f)
                self._cache = file_clients
                self._last_load_time = now
                return file_clients
        
        # 4. Fallback to .env values
        fallback = {
            "default": {
                "line_channel_secret": os.environ.get("LINE_CHANNEL_SECRET"),
                "line_channel_access_token": os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"),
                "spreadsheet_id": os.environ.get("SPREADSHEET_ID"),
                "knowledge_folder_id": os.environ.get("GOOGLE_DRIVE_FOLDER_ID"),
                "bot_name": "Mora",
                "personality": "Helpful Office Assistant"
            }
        }
        self._cache = fallback
        return fallback

    def _load_from_sheet(self, sheet_id):
        """Helper to read registry from Google Sheets API"""
        from utils.auth import get_google_credentials
        from googleapiclient.discovery import build
        
        creds = get_google_credentials()
        if not creds: return None
        
        service = build('sheets', 'v4', credentials=creds)
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range='A:G'
        ).execute()
        
        values = result.get('values', [])
        if not values or len(values) < 2:
            return None
            
        headers = values[0]
        clients = {}
        for row in values[1:]:
            if not row or not row[0]: continue
            client_id = row[0]
            config = {}
            for i, header in enumerate(headers):
                if i < len(row):
                    config[header] = row[i]
            clients[client_id] = config
            
        return clients

    def get_client(self, client_id):
        """Retrieve config for a specific client (with dynamic reload)"""
        clients = self.load_registry()
        return clients.get(client_id)

    def list_clients(self):
        """List current client IDs"""
        clients = self.load_registry()
        return list(clients.keys())

# Global registry instance
registry = ClientRegistry()
