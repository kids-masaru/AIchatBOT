import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Add koto dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.scheduler import SchedulerAgent
from core.librarian import LibrarianAgent
from core.maker import MakerAgent
from core.historian import HistorianAgent

def test_rina():
    print("\n--- Testing Rina (Scheduler) ---")
    rina = SchedulerAgent()
    
    req1 = "明日の15時から16時に『Koto連携テスト』という予定を追加して。"
    print(f"User: {req1}")
    res1 = rina.run(user_request=req1)
    print(f"Rina: {res1}\n")
    
    req2 = "さっき追加した『Koto連携テスト』という予定を削除して。"
    print(f"User: {req2}")
    res2 = rina.run(user_request=req2)
    print(f"Rina: {res2}\n")

def test_aki():
    print("\n--- Testing Aki (Librarian) ---")
    aki = LibrarianAgent()
    
    req1 = "「ママミールに関するファイル」を探して教えて。"
    print(f"User: {req1}")
    res1 = aki.run(user_request=req1)
    print(f"Aki: {res1}\n")

def test_fumi():
    print("\n--- Testing Fumi (Maker) ---")
    fumi = MakerAgent()
    
    req1 = "Google Keepに「Koto連携テストメモ」というタイトルで「初期テスト」とメモして。"
    print(f"User: {req1}")
    res1 = fumi.run(user_request=req1)
    print(f"Fumi: {res1}\n")
    
    req2 = "先ほどの「Koto連携テストメモ」に「追記テスト成功！」という文章を追記して。"
    print(f"User: {req2}")
    res2 = fumi.run(user_request=req2)
    print(f"Fumi: {res2}\n")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "rina": test_rina()
        elif sys.argv[1] == "aki": test_aki()
        elif sys.argv[1] == "fumi": test_fumi()
    else:
        test_rina()
        test_fumi()
        test_aki()
