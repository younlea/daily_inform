import json
import sys

try:
    with open('/home/younlea/source-code/daily_inform/feeds.json', 'r') as f:
        data = json.load(f)
    print("✅ feeds.json is valid.")
    print(f"Economy feeds: {len(data.get('economy', []))}")
    print(f"Robotics feeds: {len(data.get('robotics', []))}")
    for feed in data.get('robotics', [])[-3:]:
        print(f"  - New Feed: {feed['title']} ({feed['url'][:50]}...)")
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
