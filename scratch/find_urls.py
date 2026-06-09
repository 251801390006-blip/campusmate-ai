import re

log_path = r"C:\Users\Amala\.gemini\antigravity\brain\aa5cdc47-b015-4803-84d5-ae96a6b98927\.system_generated\logs\transcript.jsonl"
try:
    with open(log_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Search for railway.app URLs
    urls = set(re.findall(r'https?://[a-zA-Z0-9\-\.]+\.railway\.app\S*', content))
    print("Found Railway URLs:")
    for url in sorted(list(urls)):
        print(url)
except Exception as e:
    print("Error:", e)
