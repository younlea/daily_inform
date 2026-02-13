import sys
sys.path.append('/home/younlea/source-code/daily_inform')
from local_update import process_news_with_local_llm

print("Testing process_news_with_local_llm...")
title, summary = process_news_with_local_llm("Title", "Snippet")
print(f"Result 1: {title}, {summary}")

# Test with |||
# Since we mock LLM in test or just rely on real LLM?
# Real LLM takes time.
# I can just inspect the function code object.
import inspect
src = inspect.getsource(process_news_with_local_llm)
print("Source code of function:")
print(src)
