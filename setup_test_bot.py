
import sys
import os
import json
from googleapiclient.discovery import build

# Setup paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.google_ops import create_google_sheet, search_drive
from utils.sheets_config import save_config, DEFAULT_CONFIG, load_config

def setup():
    # 1. Create Spreadsheet
    sheet_name = "AIchatBOT_Config_TestBot_V2"
    print(f"Creating/Finding spreadsheet: {sheet_name}...")
    
    # Search first
    res = search_drive(sheet_name)
    files = res.get("files", [])
    if files:
        spreadsheet_id = files[0]["id"]
        print(f"Found existing: {spreadsheet_id}")
    else:
        new_sheet = create_google_sheet(sheet_name)
        spreadsheet_id = new_sheet.get("id")
        print(f"Created new: {spreadsheet_id}")

    if not spreadsheet_id:
        print("Failed to get spreadsheet ID")
        return

    # 2. Initialize Config
    print("Initializing config...")
    success = save_config(DEFAULT_CONFIG, spreadsheet_id)
    if success:
        print("Successfully initialized config sheet.")
    else:
        print("Failed to initialize config sheet.")
        return

    # 3. Update master_config.json
    master_path = "master_config.json"
    with open(master_path, 'r', encoding='utf-8') as f:
        master = json.load(f)
    
    # Add TestBot
    master["test_bot"] = {
        "line_channel_secret": "25d1acedbf17ed635f9dca7b6a3d7c0f",
        "line_channel_access_token": "PV1pojNw5HbjiSOz2Pqc6RL6fwz9gGiZb0OiIdSPEXlGiTMjzMUMmvXSpAEh7xzAERbDsxJ71knaO1+dRvnBM1EFjRQH4aMOZgOkK+PuTg9U25dBCARveM3AMsasG2/oI0e11SMzJcEM8rJENp1hlwdB04t89/1O/w1cDnyilFU=",
        "spreadsheet_id": spreadsheet_id,
        "bot_name": "テストボット",
        "personality": "丁寧なAIアシスタント"
    }
    
    with open(master_path, 'w', encoding='utf-8') as f:
        json.dump(master, f, ensure_ascii=False, indent=2)
    
    print("Registered 'test_bot' in master_config.json.")
    print(f"Webhook URL should be: https://[YOUR_DOMAIN]/callback/test_bot")

if __name__ == "__main__":
    setup()
