import requests

try:
    res = requests.get('http://127.0.0.1:8000/', timeout=5)
    print("Homepage response status:", res.status_code)
except Exception as e:
    print("Error connecting to server:", e)
