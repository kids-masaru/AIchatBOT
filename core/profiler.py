"""
Mora Profiler (Gemini Version)
Analyzes conversation history to update user profiles (psychological/preference models).
"""
import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
from google import genai
from utils.vector_store import _get_index, GeminiEmbedder

# Configure Gemini
api_key = os.environ.get("GEMINI_API_KEY")

class ProfilerAgent:
    def __init__(self):
        # User requested 'gemini-3-flash-preview'.
        # We use the new google-genai SDK Client.
        if not api_key:
            print("Profiler Error: GEMINI_API_KEY not found.", file=sys.stderr)
            self.client = None
        else:
            self.client = genai.Client(api_key=api_key)
            
        self.model_name = 'gemini-3-flash-preview'
        
    def run_analysis(self, user_id: str, days_back: int = 1, client_id: str = "default") -> Dict:
        """Analyze recent conversations and update profile"""
        if not self.client:
             print("Profiler Error: Client not initialized.", file=sys.stderr)
             return {}

        print(f"Profiler: Starting analysis for {user_id} using {self.model_name}...", file=sys.stderr)

        # 1. Fetch recent conversations from Pinecone
        recent_logs = self._fetch_recent_logs(user_id, days_back, client_id=client_id)
        if not recent_logs:
            print("Profiler: No new logs to analyze.", file=sys.stderr)
            return self._load_current_profile(user_id, client_id=client_id)

        # 2. Load existing profile
        current_profile = self._load_current_profile(user_id, client_id=client_id)
        
        # 3. Generate analysis prompting
        updated_profile = self._analyze_and_merge(current_profile, recent_logs)
        
        # 4. Save updated profile
        self._save_profile(user_id, updated_profile, client_id=client_id)

        print("Profiler: Profile updated successfully.", file=sys.stderr)
        return updated_profile

    def _fetch_recent_logs(self, user_id: str, days: int, client_id: str = "default") -> List[str]:
        """Fetch logs from local storage (Short-term memory approach)"""
        # The vector store approach is good for long-term recall, 
        # but for daily profiling, we want the raw recent conversation.
        try:
            from utils.storage import get_user_history
            history = get_user_history(user_id)
            
            # Extract only user messages
            # Note: history.json only keeps MAX_HISTORY (10). 
            # This is actually perfect for "daily update" as it processes what's active.
            logs = []
            for msg in history:
                if msg.get('role') == 'user':
                    logs.append(msg.get('text', ''))
            
            if not logs:
                # If local history is empty, maybe fallback to Pinecone?
                # But if local is empty, user hasn't talked recently.
                return []
                
            return logs
        except Exception as e:
            print(f"Profiler Log Fetch Error: {e}", file=sys.stderr)
            return []

    def _load_current_profile(self, user_id: str, client_id: str = "default") -> Dict:
        from utils.vector_store import get_user_profile
        return get_user_profile(user_id, client_id=client_id)

    def _save_profile(self, user_id: str, profile: Dict, client_id: str = "default"):
        from utils.vector_store import save_user_profile
        save_user_profile(user_id, profile, client_id=client_id)

    def _analyze_and_merge(self, current_profile: Dict, logs: List[str]) -> Dict:
        """Ask Gemini to update the profile based on new logs"""
        
        logs_text = "\n".join([f"- {log}" for log in logs])
        current_profile_str = json.dumps(current_profile, ensure_ascii=False, indent=2)
        
        # Get prompt from config or use default
        from utils.sheets_config import load_config
        config = load_config()
        
        system_prompt = config.get('shiori_instruction', """
        あなたは「栞（しおり）」という名の、心優しい伝記作家です。
        対象人物（ユーザー）の会話記録（Log）を読み、現在の人物プロファイル（Profile）を更新してください。
        
        【指示】
        1. 新しい会話から読み取れる「性格」「興味関心」「価値観」「悩み」「目標」を抽出してください。
        2. 現在のプロファイルと矛盾する場合は、新しい情報を優先して書き換えてください。
        3. 以前の情報で、変わっていない部分は維持してください。
        4. 出力は必ず以下のJSON形式のみで行ってください。
        5. **重要: すべての項目（リストの中身など）は必ず日本語で出力してください。**
        
        {{
            "name": "推定または既知の名前",
            "personality_traits": ["特徴1", "特徴2", ...],
            "interests": ["興味1", "興味2", ...],
            "values": ["価値観1", ...],
            "current_goals": ["目標1", ...],
            "summary": "人物像の簡潔な要約（200文字以内）"
        }}
        """)

        prompt = f"""
        {system_prompt}
        
        【現在のプロファイル】
        {current_profile_str}
        
        【新しい会話記録（断片）】
        {logs_text}
        """
        
        try:
            # Use new SDK method with simple retry logic for transient network/API timeouts
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = self.client.models.generate_content(
                        model=self.model_name,
                        contents=prompt,
                        config={'response_mime_type': 'application/json'}
                    )
                    break # Success
                except Exception as inner_e:
                    if attempt < max_retries - 1:
                        print(f"Profiler API attempt {attempt+1} failed: {inner_e}. Retrying in 5s...", file=sys.stderr)
                        time.sleep(5)
                    else:
                        raise inner_e # Re-raise to be caught by outer block if all retries fail

            text = response.text.strip()
            
            # Clean up markdown code blocks if present
            if "```json" in text:
                import re
                match = re.search(r'```json\n(.*?)\n```', text, re.DOTALL)
                if match:
                    text = match.group(1)
            elif "```" in text:
                 text = text.replace("```", "")
            
            return self._safe_parse_profile(text, current_profile)
        except Exception as e:
            print(f"Profiler Logic/API Error (Analysis Skipped): {type(e).__name__}: {e}", file=sys.stderr)
            # Return current profile instead of crashing, so we don't wipe data
            return current_profile

    def _safe_parse_profile(self, text, current_profile):
        """Parse Gemini's JSON response, ensuring it's always a dict"""
        try:
            result = json.loads(text)
            # Gemini may rarely return a list like [{"name": ...}] instead of {"name": ...}
            if isinstance(result, list):
                if result and isinstance(result[0], dict):
                    return result[0]
                return current_profile
            if not isinstance(result, dict):
                return current_profile
            return result
        except (json.JSONDecodeError, Exception) as e:
            print(f"Profiler JSON parse error: {e}", file=sys.stderr)
            return current_profile

# Global Instance
profiler = ProfilerAgent()
