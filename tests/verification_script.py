import sys
import os
import time
from dotenv import load_dotenv

# Load env vars
load_dotenv()

# Add parent directory to path so we can import core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agent import get_gemini_response

TEST_USER_ID = "test_verifier"

def log(msg):
    print(msg)
    with open("verification_result.txt", "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def run_test(name, prompt):
    log(f"\n{'='*20} ORCHESTRATION TEST: {name} {'='*20}")
    log(f"User Prompt: {prompt}")
    log("-" * 60)
    
    try:
        # Measure time
        start_time = time.time()
        
        # Call Mora (Router)
        # Note: get_gemini_response might print to stdout/stderr, verifying that is harder.
        # But we capture the return value which is the most important part.
        response = get_gemini_response(TEST_USER_ID, prompt)
        
        elapsed = time.time() - start_time
        
        log(f"\n[Mora Response] ({elapsed:.2f}s):")
        log(response)
        log("-" * 60)
        
    except Exception as e:
        log(f"ERROR: {e}")

if __name__ == "__main__":
    # Clear previous log
    with open("verification_result.txt", "w", encoding="utf-8") as f:
        f.write("Starting Verification Run...\n")
        
    log("Starting Mora Multi-Agent Verification...")
    
    # 1. Test Fumi (Creation)
    run_test("Fumi (Creator)", "「Moraシステム稼働テスト」というタイトルのGoogleドキュメントを作成して。「動作確認済み」とだけ書いておいて。")
    
    # Wait a bit
    time.sleep(2)

    # 2. Test Aki (Organization)
    run_test("Aki (Librarian)", "さっき作った「Moraシステム稼働テスト」というファイルを、「テスト結果_Temp」というフォルダを作ってそこに移動して。")

    time.sleep(2)

    # 3. Test Rina (Scheduler)
    run_test("Rina (Scheduler)", "2027年1月1日の朝10時に「Mora動作テスト」という予定を入れて。")
    
    time.sleep(2)

    # 4. Test Ren (Communicator)
    run_test("Ren (Communicator)", "明日遅れる旨を上司に伝えるメールの下書きを書いて。ものすごく丁寧に。")
    
    time.sleep(2)

    # 5. Test Toki (Historian)
    run_test("Toki (Historian)", "私のプロファイルについて、知っていることを教えて。")

    log("\nVerification Complete.")
