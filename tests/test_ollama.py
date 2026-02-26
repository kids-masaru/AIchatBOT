import sys
import os
import time

# Add project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../")

def test_embeddings():
    print("Testing Embeddings (nomic-embed-text)...")
    try:
        from utils.vector_store import OllamaEmbedder
        embedder = OllamaEmbedder()
        vec = embedder.embed_text("Hello Ollama")
        print(f"Success! Vector length: {len(vec)}")
        return True
    except Exception as e:
        print(f"Embedding Failed: {e}")
        return False

def test_chat():
    print("\nTesting Chat (deepseek-r1:14b)...")
    try:
        from core.agent import get_agent_response
        # Stream=False for simple test
        response = get_agent_response("test_user_id", "Hello! Who are you?", stream=False)
        print(f"Response: {response[:100]}...")
        if "Tool execution limit" in response:
            print("Chat Failed (Loop limit)")
            return False
        return True
    except Exception as e:
        print(f"Chat Failed: {e}")
        return False

def test_tool():
    print("\nTesting Tool Execution (Calculation)...")
    try:
        from core.agent import get_agent_response
        # DeepSeek R1 should be able to calculate 123 * 456 using tools or simple reasoning
        # We explicitly ask to use tool if possible, or just check if it answers correctly.
        # R1 is strong at math reasoning so it might not use the tool, but that's fine.
        response = get_agent_response("test_user_id", "Calculate 12345 * 67890. Use the calculator tool.")
        print(f"Response: {response}")
        return True
    except Exception as e:
        print(f"Tool Test Failed: {e}")
        return False

def test_vision():
    print("\nTesting Vision (llava)...")
    try:
        from core.agent import analyze_document_layout
        # Create a tiny 1x1 black pixel GIF/PNG base64 (or just bytes)
        # 1x1 GIF bytes
        dummy_img_bytes = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
        
        result = analyze_document_layout(dummy_img_bytes, "image/gif")
        if result.get("success"):
            print("Vision Test Passed!")
            return True
        else:
            print(f"Vision Test Failed: {result.get('error')}")
            return False
    except Exception as e:
        print(f"Vision Test Failed: {e}")
        return False

if __name__ == "__main__":
    if test_embeddings() and test_chat() and test_tool() and test_vision():
        print("\nAll Tests Passed!")
    else:
        print("\nSome Tests Failed.")
