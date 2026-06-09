import requests

session = requests.Session()

# Get login page
login_page = session.get('http://127.0.0.1:8000/auth/login')
print("Login Page status:", login_page.status_code)

# Post login credentials
login_response = session.post('http://127.0.0.1:8000/auth/login', data={
    'email': 'demo@university.edu',
    'password': 'demo1234'
}, allow_redirects=True)
print("Login status:", login_response.status_code)

# Access resume-analyzer page
res = session.get('http://127.0.0.1:8000/resume-analyzer')
print("Resume Analyzer page response status:", res.status_code)
if res.status_code == 500:
    print(res.text[:1000])
