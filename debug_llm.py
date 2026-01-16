import ollama
import feedparser
import re

PROMPT_FILE = 'prompt.md'
LOCAL_MODEL = "llama3"

def load_prompt_template():
    with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
        return f.read()

def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    text = re.sub(cleanr, '', raw_html)
    return text.replace('&nbsp;', ' ').strip()

def test_feed():
    url = "https://news.google.com/rss/search?q=stock+market+economy+korea+usa&hl=ko&gl=KR&ceid=KR:ko"
    print(f"Fetching from: {url}")
    feed = feedparser.parse(url, agent="Mozilla/5.0")
    
    if not feed.entries:
        print("No entries found!")
        return

    entry = feed.entries[0]
    print(f"Original Title: {entry.title}")
    
    raw_snippet = clean_html(entry.get('description', entry.get('summary', '')))
    print(f"Original Snippet (Cleaned): {raw_snippet[:100]}...")

    template = load_prompt_template()
    final_prompt = template.replace("{title}", entry.title).replace("{snippet}", raw_snippet)
    
    print("\n--- Sending to LLM ---")
    try:
        response = ollama.chat(model=LOCAL_MODEL, messages=[{'role': 'user', 'content': final_prompt}])
        result_text = response['message']['content'].strip()
        print(f"LLM Raw Output:\n{result_text}")
    except Exception as e:
        print(f"LLM Error: {e}")

if __name__ == "__main__":
    test_feed()
