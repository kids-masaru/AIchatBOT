import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.sheets_config import load_config, save_config, DEFAULT_CONFIG

def update_sheet_config():
    """
    Force update the Google Sheet configuration with the new DEFAULT_CONFIG values.
    Specifically targeting 'shiori_instruction'.
    """
    print("Loading current config from Sheets...")
    current_config = load_config()
    
    # Check if update is needed
    new_instruction = DEFAULT_CONFIG['shiori_instruction']
    current_instruction = current_config.get('shiori_instruction', '')
    
    if new_instruction == current_instruction:
        print("Config is already up to date.")
        return
    
    print("Updating 'shiori_instruction' in config...")
    # Update the specific key
    current_config['shiori_instruction'] = new_instruction
    
    # Save back to sheet
    if save_config(current_config):
        print("Successfully updated configuration in Google Sheets.")
    else:
        print("Failed to save configuration.")

if __name__ == "__main__":
    update_sheet_config()
