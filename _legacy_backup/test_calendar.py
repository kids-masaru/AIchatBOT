
import sys
import os
import datetime
from dotenv import load_dotenv

# Add current dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from tools.google_ops import list_calendar_events, create_calendar_event

def test_calendar():
    print("--- Calendar Integration Test ---", file=sys.stderr)
    
    # Check Env Vars
    service_account = os.environ.get('GOOGLE_SERVICE_ACCOUNT_KEY')
    print(f"Service Account Key present: {'Yes' if service_account else 'No'}", file=sys.stderr)

    print("\n1. Testing Create Event...", file=sys.stderr)
    tomorrow = (datetime.datetime.utcnow() + datetime.timedelta(days=1)).isoformat()
    try:
        create_result = create_calendar_event(
            summary="Koto AI Test Event",
            start_time=tomorrow,
            location="Virtual"
        )
        
        if create_result.get('error'):
            print(f"CREATE FAILED: {create_result['error']}", file=sys.stderr)
        else:
            print(f"CREATE SUCCESS: {create_result.get('link')}", file=sys.stderr)
            
    except Exception as e:
        print(f"CREATE EXCEPTION: {e}", file=sys.stderr)

    print("\n2. Testing List Events...", file=sys.stderr)
    try:
        list_result = list_calendar_events()
        
        if list_result.get('error'):
             print(f"LIST FAILED: {list_result['error']}", file=sys.stderr)
        else:
            print(f"LIST SUCCESS: {list_result.get('count')} events found.", file=sys.stderr)
            for evt in list_result.get('events', [])[:3]:
                print(f"- {evt.get('summary')} ({evt.get('start', {}).get('dateTime')})", file=sys.stderr)

    except Exception as e:
        print(f"LIST EXCEPTION: {e}", file=sys.stderr)

if __name__ == "__main__":
    test_calendar()
