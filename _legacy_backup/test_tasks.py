from dotenv import load_dotenv
import os
import sys

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.google_ops import list_tasks, add_task

def test_tasks():
    print("Testing Google Tasks Integration...")
    
    # 1. Test Listing Tasks
    print("\n[1] Listing Tasks...")
    result = list_tasks()
    if "error" in result:
        print(f"❌ Failed to list tasks: {result['error']}")
        return
    else:
        print(f"✅ Successfully listed tasks. Count: {result.get('count', 0)}")
        for t in result.get('tasks', [])[:3]:
            print(f"   - {t['title']}")

    # 2. Test Adding Task
    print("\n[2] Adding Test Task...")
    add_result = add_task("Test Task from Koto Debugger")
    if "error" in add_result:
        print(f"❌ Failed to add task: {add_result['error']}")
    else:
        print(f"✅ Successfully added task: {add_result.get('task', {}).get('title')}")

if __name__ == "__main__":
    test_tasks()
