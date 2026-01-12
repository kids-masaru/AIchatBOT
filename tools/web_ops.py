"""
Web operations - Google search and URL fetching
"""
import re
import urllib.request
import sys

try:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        # Try newer package name
        from ddgs import DDGS
    SEARCH_AVAILABLE = True
except ImportError:
    SEARCH_AVAILABLE = False
    print("duckduckgo-search (ddgs) not available", file=sys.stderr)





def _google_custom_search(query, api_key, cse_id, num_results=3):
    """
    Search using Google Custom Search JSON API
    Reliable but requires setup.
    """
    try:
        from googleapiclient.discovery import build
        service = build("customsearch", "v1", developerKey=api_key)
        res = service.cse().list(q=query, cx=cse_id, num=num_results).execute()
        
        items = res.get('items', [])
        results = []
        for item in items:
            results.append({
                "title": item.get('title', 'No Title'),
                "url": item.get('link', ''),
                "snippet": item.get('snippet', '')
            })
        return results
    except Exception as e:
        print(f"Google API Search error: {e}", file=sys.stderr)
        return []


def google_web_search(query, num_results=3):
    """
    Execute Web search and return top URLs.
    Priority:
    1. Google Custom Search API (Reliable, requires env set)
    2. DuckDuckGo (Free, but often blocked on Vercel)
    """
    import os
    
    # 1. Try Google Custom Search API first (if configured)
    api_key = os.environ.get('GOOGLE_API_KEY') or os.environ.get('GEMINI_API_KEY') # Fallback to Gemini key if same project
    cse_id = os.environ.get('GOOGLE_CSE_ID')
    
    if api_key and cse_id:
        print("Using Google Custom Search API...", file=sys.stderr)
        results = _google_custom_search(query, api_key, cse_id, num_results)
        if results:
            return {
                "success": True,
                "query": query,
                "results": results,
                "count": len(results)
            }
        print("Google API returned no results, falling back to DDG...", file=sys.stderr)

    # 2. Fallback to DuckDuckGo (Original Logic)
    try:
        if not SEARCH_AVAILABLE:
            api_status = "(Google API not configured)" if not (api_key and cse_id) else "(Google API failed)"
            return {"error": f"検索機能が利用できません {api_status}"}
        
        print("Using DuckDuckGo Search...", file=sys.stderr)
        # Execute search
        search_results = []
        # Set timeout to avoid Reply Token expiration
        # Suppress the warning by using the package correctly if we can, 
        # but the warning is internal to the library's packaging.
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            # Create DDGS instance (context manager is safer)
            with DDGS(timeout=15) as ddgs:
                # 1. Try 'html' backend for JP
                try:
                    results = list(ddgs.text(query, region='jp-jp', max_results=num_results, backend='html'))
                except Exception as e:
                    print(f"DDG JP Search Error: {e}", file=sys.stderr)
                    results = []
                
                # 2. If empty, try 'lite' backend (less blocked)
                if not results:
                     try:
                        print("JP empty, retrying with lite backend...", file=sys.stderr)
                        results = list(ddgs.text(query, region='jp-jp', max_results=num_results, backend='lite'))
                     except Exception as e:
                        print(f"DDG Lite Error: {e}", file=sys.stderr)

                # 3. If still empty, try global
                if not results:
                    try:
                        print("JP search empty, trying global...", file=sys.stderr)
                        results = list(ddgs.text(query, region='wt-wt', max_results=num_results, backend='html'))
                    except Exception as e:
                        print(f"DDG Global Search Error: {e}", file=sys.stderr)
                        results = []

                for r in results:
                    search_results.append({
                        "title": r.get('title', 'No Title'),
                        "url": r.get('href', ''),
                        "snippet": r.get('body', '') or r.get('snippet', '')
                    })
        
        # Fallback: If no results found (likely IP blocked), return a direct search URL
        if not search_results:
            print("Search returned 0 results. Using fallback URL.", file=sys.stderr)
            search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
            search_results.append({
                "title": f"Google検索結果 (ここをクリック): {search_url}",
                "url": search_url,
                "snippet": f"検索結果を読み取れませんでした。こちらのリンクから直接確認してください: {search_url}"
            })
        
        return {
            "success": True,
            "query": query,
            "results": search_results,
            "count": len(search_results)
        }
    except Exception as e:
        print(f"Search error: {e}", file=sys.stderr)
        return {"error": f"検索エラー: {str(e)}"}


def fetch_url(url):
    """
    Fetch content from URL and extract text
    Removes HTML tags for clean text output
    """
    try:
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        with urllib.request.urlopen(req, timeout=10) as res:
            content = res.read().decode('utf-8', errors='ignore')
            
            # Simple HTML to text (remove tags)
            content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
            content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
            content = re.sub(r'<[^>]+>', ' ', content)
            content = re.sub(r'\s+', ' ', content).strip()
            
            # Truncate if too long
            if len(content) > 5000:
                content = content[:5000] + "..."
            
            return {"success": True, "content": content, "url": url}
    except Exception as e:
        return {"error": f"URL取得エラー: {str(e)}"}
