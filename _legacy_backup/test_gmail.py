import sys
import os
from dotenv import load_dotenv
import json

# Add current dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from tools.google_ops import list_gmail

def test_gmail():
    print("--- Gmail Integration Test ---", file=sys.stderr)
    
    # Check Env Vars
    service_account = os.environ.get('GOOGLE_SERVICE_ACCOUNT_KEY')
    delegated_user = os.environ.get('GOOGLE_DELEGATED_USER')
    
    print(f"Service Account Key present: {'Yes' if service_account else 'No'}", file=sys.stderr)
    print(f"Delegated User: {delegated_user}", file=sys.stderr)
    
    if not delegated_user:
        print("ERROR: GOOGLE_DELEGATED_USER is missing in .env", file=sys.stderr)
        return

    print("\nAttempting to fetch emails (never_than:1d)...", file=sys.stderr)
    try:
        # Fetch emails from the last 24 hours
        result = list_gmail(query="newer_than:1d", max_results=5)
        
        if result.get('error'):
            print(f"FAILED: {result['error']}", file=sys.stderr)
        else:
            print("SUCCESS!", file=sys.stderr)
            print(f"Count: {result.get('count')}", file=sys.stderr)
            for email in result.get('emails', []):
                print(f"- [{email['date']}] {email['subject']} (Snippet: {email.get('snippet', '')[:30]}...)", file=sys.stderr)
                
    except Exception as e:
        print(f"EXCEPTION: {str(e)}", file=sys.stderr)

if __name__ == "__main__":
    test_gmail()
