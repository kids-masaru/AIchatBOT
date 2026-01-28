"""
Vector Store - Pinecone-based persistent memory for conversation history
Enables RAG (Retrieval Augmented Generation) for KOTO
Uses Gemini API for embeddings and Pinecone for storage
"""
import os
import sys
import json
import time
import urllib.request
from datetime import datetime
from typing import List, Dict, Optional

# Lazy loading to avoid slow startup
_pinecone_index = None
_init_error = None

INDEX_NAME = "koto-memory"
DIMENSION = 768  # Gemini text-embedding-004 dimension
PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY', '')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')


class GeminiEmbedder:
    """Helper class to get embeddings from Gemini API"""
    
    def embed_text(self, text: str) -> List[float]:
        """Get embedding for a single text"""
        if not GEMINI_API_KEY:
            return self._simple_embedding(text)
            
        try:
            return self._get_gemini_embedding(text)
        except Exception as e:
            print(f"Embedding error: {e}", file=sys.stderr)
            return self._simple_embedding(text)

    def _get_gemini_embedding(self, text: str) -> List[float]:
        """Get embedding from Gemini API"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={GEMINI_API_KEY}"
        
        data = {
            "model": "models/text-embedding-004",
            "content": {"parts": [{"text": text[:2000]}]}  # Truncate to avoid token limits
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=10) as res:
            result = json.loads(res.read().decode('utf-8'))
            return result.get('embedding', {}).get('values', [])
    
    def _simple_embedding(self, text: str) -> List[float]:
        """Fallback: Simple hash-based embedding (768 dimensions)"""
        import hashlib
        # Create a deterministic but simple embedding
        hash_bytes = hashlib.sha256(text.encode('utf-8')).digest() * 24  # 768 bytes
        return [b / 255.0 for b in hash_bytes[:768]]


def _get_index():
    """Get or create Pinecone index (lazy load)"""
    global _pinecone_index, _init_error
    
    if _pinecone_index is not None:
        return _pinecone_index
        
    if not PINECONE_API_KEY:
        _init_error = "PINECONE_API_KEY not set"
        return None
    
    try:
        from pinecone import Pinecone, ServerlessSpec
        
        pc = Pinecone(api_key=PINECONE_API_KEY)
        
        # Check if index exists
        existing_indexes = pc.list_indexes().names()
        
        if INDEX_NAME not in existing_indexes:
            # Create index if not exists
            print(f"Creating Pinecone index: {INDEX_NAME}...", file=sys.stderr)
            pc.create_index(
                name=INDEX_NAME,
                dimension=DIMENSION,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
            # Wait for index to be ready
            while not pc.describe_index(INDEX_NAME).status['ready']:
                time.sleep(1)
        
        _pinecone_index = pc.Index(INDEX_NAME)
        return _pinecone_index
        
    except Exception as e:
        _init_error = str(e)
        print(f"Error initializing Pinecone: {e}", file=sys.stderr)
        return None


def save_conversation(user_id: str, role: str, text: str, metadata: Optional[Dict] = None) -> bool:
    """Save conversation message to Pinecone"""
    index = _get_index()
    if index is None:
        return False
    
    try:
        # Generate embedding
        embedder = GeminiEmbedder()
        vector = embedder.embed_text(text)
        
        # Create unique ID
        doc_id = f"{user_id}_{datetime.now().isoformat()}_{role}"
        
        # Prepare metadata
        doc_metadata = {
            "user_id": user_id,
            "role": role,
            "text": text, # Store text in metadata for retrieval
            "timestamp": datetime.now().isoformat(),
        }
        if metadata:
            doc_metadata.update(metadata)
        
        # Upsert to Pinecone
        index.upsert(vectors=[(doc_id, vector, doc_metadata)])
        
        return True
    except Exception as e:
        print(f"Error saving to Pinecone: {e}", file=sys.stderr)
        return False


def search_relevant_context(user_id: str, query: str, n_results: int = 5) -> List[Dict]:
    """Search for relevant past conversations"""
    index = _get_index()
    if index is None:
        return []
    
    try:
        # Generate embedding for query
        embedder = GeminiEmbedder()
        vector = embedder.embed_text(query)
        
        # Search Pinecone
        results = index.query(
            vector=vector,
            top_k=n_results,
            filter={"user_id": user_id},
            include_metadata=True
        )
        
        # Format results
        relevant_context = []
        for match in results.matches:
            metadata = match.metadata or {}
            relevant_context.append({
                "text": metadata.get("text", ""),
                "role": metadata.get("role", "unknown"),
                "timestamp": metadata.get("timestamp", ""),
                "relevance": match.score
            })
        
        return relevant_context
    except Exception as e:
        print(f"Error searching Pinecone: {e}", file=sys.stderr)
        return []


def get_context_summary(user_id: str, query: str, max_tokens: int = 500) -> str:
    """Get context summary for AI prompt"""
    relevant = search_relevant_context(user_id, query, n_results=5)
    
    if not relevant:
        return ""
    
    # Build context summary
    context_parts = []
    total_chars = 0
    max_chars = max_tokens * 3
    
    # Sort by timestamp (oldest first) to maintain conversation flow
    # or keep relevance order? Usually relevance is better for RAG, 
    # but context flow is easier to read if sorted.
    # Let's keep relevance for now as they are independent snippets.
    
    for item in relevant:
        if total_chars >= max_chars:
            break
        
        role_label = "ユーザー" if item["role"] == "user" else "KOTO"
        text = item["text"][:200]
        
        entry = f"[{role_label}] {text}"
        context_parts.append(entry)
        total_chars += len(entry)
    
    if context_parts:
        return "【過去の関連会話】\n" + "\n".join(context_parts) + "\n"
    
    return ""


def get_collection_stats() -> Dict:
    """Get Pinecone index stats"""
    global _init_error
    index = _get_index()
    
    if index is None:
        return {"status": "not_initialized", "init_error": _init_error}
    
    try:
        stats = index.describe_index_stats()
        return {
            "status": "ok",
            "total_documents": stats.total_vector_count,
            "collection_name": INDEX_NAME,
            "provider": "pinecone"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

# --- Profile Persistence (Phase 5) ---

def get_user_profile(user_id: str) -> Dict:
    """Retrieve user profile from Pinecone (stored as special vector)"""
    index = _get_index()
    if index is None:
        return {}
        
    try:
        # Fetch by specific ID
        profile_id = f"profile:{user_id}"
        fetch_response = index.fetch(ids=[profile_id])
        
        if profile_id in fetch_response.vectors:
            vector_data = fetch_response.vectors[profile_id]
            # Profile data is stored in metadata['json_data'] as string
            if vector_data.metadata and 'json_data' in vector_data.metadata:
                return json.loads(vector_data.metadata['json_data'])
                
        return {}
    except Exception as e:
        print(f"Error fetching profile: {e}", file=sys.stderr)
        return {}

def save_user_profile(user_id: str, profile_data: Dict) -> bool:
    """Save user profile to Pinecone"""
    index = _get_index()
    if index is None:
        return False
        
    try:
        profile_id = f"profile:{user_id}"
        
        # Serialize profile to JSON string
        json_str = json.dumps(profile_data, ensure_ascii=False)
        
        # Use a dummy vector (all 0.1s to avoid "all integers zero" validation error)
        # Pinecone requires a vector, and it must not be all zeros in some metric configs.
        dummy_vector = [0.1] * DIMENSION
        
        # Upsert
        index.upsert(vectors=[(
            profile_id, 
            dummy_vector, 
            {
                "type": "profile",
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "json_data": json_str # Store actual data here
            }
        )])
        return True
    except Exception as e:
        print(f"Error saving profile: {e}", file=sys.stderr)
        return False

# --- Knowledge Retrieval (Phase 6 - RAG) ---

def save_knowledge_vector(doc_id: str, text: str, metadata: Dict) -> bool:
    """Save knowledge document chunk to Pinecone (namespace='knowledge')"""
    index = _get_index()
    if index is None: return False
    
    try:
        embedder = GeminiEmbedder()
        vector = embedder.embed_text(text)
        
        # Upsert to 'knowledge' namespace
        index.upsert(
            vectors=[(doc_id, vector, metadata)], 
            namespace="knowledge"
        )
        return True
    except Exception as e:
        print(f"Error saving knowledge: {e}", file=sys.stderr)
        return False

def search_knowledge_base(query: str, n_results: int = 5) -> List[Dict]:
    """Search knowledge base (namespace='knowledge')"""
    index = _get_index()
    if index is None: return []
    
    try:
        embedder = GeminiEmbedder()
        vector = embedder.embed_text(query)
        
        results = index.query(
            vector=vector,
            top_k=n_results,
            namespace="knowledge",
            include_metadata=True
        )
        
        hits = []
        for match in results.matches:
            if match.score > 0.5: # Relevance threshold
                hits.append({
                    "text": match.metadata.get("text", ""),
                    "source": match.metadata.get("source", "unknown"),
                    "score": match.score
                })
        return hits
    except Exception as e:
        print(f"Error searching knowledge: {e}", file=sys.stderr)
        return []
