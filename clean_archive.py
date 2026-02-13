import json
import os

ARCHIVE_FILE = 'news_archive.json'

def clean_archive():
    if not os.path.exists(ARCHIVE_FILE):
        print("Archive file not found.")
        return

    with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print("JSON Decode Error")
            return

    initial_count = len(data)
    valid_data = []
    
    for item in data:
        # 1. Check for missing title (caused by sed delete)
        if 'title' not in item:
            print(f"Removing item with missing title (Link: {item.get('link', 'No Link')})")
            continue
            
        # 2. Check for garbage in title (????)
        if '????' in item['title']:
            print(f"Removing item with garbage title: {item['title']}")
            continue
            
        # 3. Check for markdown artifacts in title (**)
        if item['title'].strip().startswith('**'):
            print(f"Removing item with markdown in title: {item['title']}")
            continue

        valid_data.append(item)

    if len(valid_data) < initial_count:
        with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
            json.dump(valid_data, f, ensure_ascii=False, indent=2)
        print(f"✅ Cleaned archive. Removed {initial_count - len(valid_data)} items.")
    else:
        print("No items needed cleaning.")

if __name__ == "__main__":
    clean_archive()
