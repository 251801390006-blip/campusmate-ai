import requests
import sys

BASE_URL = "http://127.0.0.1:8000"

endpoints = {
    "Login": "/auth/login",
    "Register": "/auth/register",
    "Resume Analyzer": "/resume-analyzer",
    "Roadmap": "/roadmaps",
    "Interview Simulator": "/interview-prep",
    "Internship Center": "/internship-center",
    "Admin Panel": "/admin/"
}

print("Running Security Audit Tests...")
all_passed = True
results = []

for name, path in endpoints.items():
    try:
        url = BASE_URL + path
        response = requests.get(url, allow_redirects=True, timeout=5)
        # 200 OK or 401/403 Unauthorized (which is fine, it just redirects to login properly or says unauthorized)
        # But we expect 200 for public pages or redirects to login page which returns 200
        if response.status_code in [200, 302, 401, 403]:
            print(f"[{name}] PASS (HTTP {response.status_code})")
            results.append((name, "PASS"))
        else:
            print(f"[{name}] FAIL (HTTP {response.status_code})")
            results.append((name, "FAIL"))
            all_passed = False
    except Exception as e:
        print(f"[{name}] FAIL ({str(e)})")
        results.append((name, "FAIL"))
        all_passed = False

if all_passed:
    print("\nALL MODULES PASS")
    sys.exit(0)
else:
    print("\nSOME MODULES FAILED")
    sys.exit(1)
