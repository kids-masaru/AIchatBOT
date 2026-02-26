"""
Vector Store Management using Pinecone and Gemini Embeddings
"""
import os
import sys
import json
import time
from typing import List, Dict, Optional, Any
from google import genai
from pinecone import Pinecone, ServerlessSpec

# Config
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
PINECONE_ENV = "us-east-1" 
INDEX_NAME = "koto-memory-v2"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

class GeminiEmbedder:
    def embed_text(self, text: str) -> List[float]:
        if not GEMINI_API_KEY:
            return self._simple_embedding(text)
        try:
            return self._get_gemini_embedding(text)
        except Exception as e:
            print(f"Embedding error: {e}", file=sys.stderr)
            return self._simple_embedding(text)

    def _get_gemini_embedding(self, text: str) -> List[float]:
        client = genai.Client(api_key=GEMINI_API_KEY)
        # Use 'gemini-embedding-001' (widely available)
        result = client.models.embed_content(
            model="models/gemini-embedding-001",
            contents=text
        )
        return result.embeddings[0].values

    def _simple_embedding(self, text: str, dim: int = 768) -> List[float]:
        import hashlib
        hash_obj = hashlib.sha256(text.encode())
        hash_digest = hash_obj.digest()
        
        vector = []
        for i in range(dim):
            byte_val = hash_digest[i % len(hash_digest)]
            float_val = (byte_val / 255.0) * 2 - 1 
            vector.append(float_val)
        return vector

_pinecone_index = None

def _get_index():
    global _pinecone_index
    if _pinecone_index:
        return _pinecone_index
        
    if not PINECONE_API_KEY:
        print("Pinecone API Key missing", file=sys.stderr)
        return None
        
    try:
        pc = Pinecone(api_key=PINECONE_API_KEY)
        if INDEX_NAME not in pc.list_indexes().names():
             pc.create_index(
                name=INDEX_NAME, 
                dimension=3072, 
                metric='cosine',
                spec=ServerlessSpec(cloud='aws', region='us-east-1')
            )
        _pinecone_index = pc.Index(INDEX_NAME)
        return _pinecone_index
    except Exception as e:
        print(f"Pinecone init error: {e}", file=sys.stderr)
        return None

def save_conversation(user_id: str, role: str, text: str, metadata: Optional[Dict] = None) -> bool:
    index = _get_index()
    if index is None: return False
    
    try:
        embedder = GeminiEmbedder()
        vector = embedder.embed_text(text)
        
        timestamp = datetime.now().timestamp()
        msg_id = f"{user_id}_{int(timestamp)}_{hash(text)}"
        
        meta = {
            "user_id": user_id,
            "role": role,
            "text": text,
            "timestamp": timestamp,
            "type": "conversation"
        }
        if metadata:
            meta.update(metadata)
            
        index.upsert(vectors=[(msg_id, vector, meta)])
        return True
    except Exception as e:
        print(f"Save conversation error: {e}", file=sys.stderr)
        return False

def search_similar_conversations(user_id: str, query_text: str, top_k: int = 5) -> List[Dict]:
    index = _get_index()
    if index is None: return []
    
    try:
        embedder = GeminiEmbedder()
        vector = embedder.embed_text(query_text)
        
        result = index.query(
            vector=vector,
            top_k=top_k,
            filter={"user_id": user_id, "type": "conversation"},
            include_metadata=True
        )
        
        matches = []
        for match in result['matches']:
            matches.append(match['metadata'])
            
        return matches
    except Exception as e:
        print(f"Search error: {e}", file=sys.stderr)
        return []

def save_user_profile(user_id: str, profile_data: Dict) -> bool:
    # Save as special document in Pinecone or separate DB?
    # For now, let's assume it's stored in a separate namespace or just distinct ID
    # But Pinecone overwrites by ID.
    index = _get_index()
    if index is None: return False
    
    try:
        # Profile doesn't technically need embedding if we only fetch by ID,
        # but we might want to search profiles? 
        # For Koto, we usually just GET profile by ID.
        # Let's use simple dummy vector or embed the summary.
        
        profile_text = json.dumps(profile_data, ensure_ascii=False)
        embedder = GeminiEmbedder()
        vector = embedder.embed_text(profile_text[:1000]) # Embed summary
        
        doc_id = f"profile_{user_id}"
        meta = {
            "user_id": user_id,
            "type": "profile",
            "profile_json": profile_text,
            "updated_at": datetime.now().timestamp()
        }
        
        index.upsert(vectors=[(doc_id, vector, meta)])
        return True
    except Exception as e:
        print(f"Save profile error: {e}", file=sys.stderr)
        return False

def get_user_profile(user_id: str) -> Dict:
    index = _get_index()
    if index is None: return {}
    
    try:
        doc_id = f"profile_{user_id}"
        result = index.fetch(ids=[doc_id])
        
        if doc_id in result['vectors']:
            json_str = result['vectors'][doc_id]['metadata']['profile_json']
            return json.loads(json_str)
        return {}
    except Exception as e:
        print(f"Get profile error: {e}", file=sys.stderr)
        return {}
    
def get_context_summary(user_id: str, query: str) -> str:
    """Get summarized context from RAG"""
    matches = search_similar_conversations(user_id, query)
    if not matches:
        return ""
        
    summary = "【過去の関連会話】\n"
    for m in matches:
        role = "ユーザー" if m['role'] == 'user' else "コト"
        summary += f"- {role}: {m['text']}\n"
    return summary

from datetime import datetime
