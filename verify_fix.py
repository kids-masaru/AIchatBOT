import sys
import os
import datetime
from dotenv import load_dotenv

load_dotenv()

# Add root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def verify_all():
    print("=== Verification Start ===")
    
    # 1. Verify Timezone (JST)
    from datetime import timezone, timedelta
    # Use explicit TZ for check
    jst = timezone(timedelta(hours=9))
    now = datetime.datetime.now(jst)
    print(f"Current JST Time: {now.strftime('%Y-%m-%d %H:%M:%S %z')}")
    if now.tzinfo != jst:
        print("FAIL: Timezone is not JST")
    else:
        print("PASS: Timezone is JST")

    # 2. Verify Config Loading
    print("\n[Config Load Test]")
    try:
        from utils.sheets_config import load_config
        config = load_config()
        # Avoid printing non-ASCII name
        user_name = config.get('user_name', 'Unknown')
        print(f"Loaded User Name Length: {len(user_name)}")
        print("PASS: Config loaded")
    except Exception as e:
        print(f"FAIL: Config load error: {str(e)}")

    # 3. Verify Vector Store (Profile Save)
    print("\n[Vector Store Test]")
    try:
        from utils.vector_store import save_user_profile, get_user_profile
        test_id = "test_user_verification"
        test_profile = {
            "name": "Test User", 
            "summary": "Verification Test", 
            "timestamp": str(now)
        }
        
        print(f"Saving profile for {test_id}...")
        if save_user_profile(test_id, test_profile):
            print("Save returned True")
            
            # Read back
            print("Reading back...")
            loaded = get_user_profile(test_id)
            print(f"Loaded Name: {loaded.get('name')}")
            
            if loaded.get("name") == "Test User":
                print("PASS: Profile matched")
            else:
                print("FAIL: Profile content mismatch")
        else:
            print("FAIL: Save returned False")
    except Exception as e:
        print(f"FAIL: Vector Store error: {str(e)}")

    print("\n=== Verification End ===")

if __name__ == "__main__":
    # Force stdout to utf-8 if possible, or just ignore errors
    if sys.stdout.encoding.lower() != 'utf-8':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    verify_all()
