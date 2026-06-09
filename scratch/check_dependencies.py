import os
import re
import sys

# Get all python files in app and main.py
py_files = []
for root, dirs, files in os.walk('app'):
    for f in files:
        if f.endswith('.py'):
            py_files.append(os.path.join(root, f))
py_files.append('main.py')

# Parse imports
imported_modules = set()
for path in py_files:
    with open(path, 'r', encoding='utf-8', errors='ignore') as file:
        content = file.read()
        
    # Find "import module" or "from module import ..."
    matches1 = re.findall(r'^\s*import\s+([a-zA-Z0-9_]+)', content, re.MULTILINE)
    matches2 = re.findall(r'^\s*from\s+([a-zA-Z0-9_]+)', content, re.MULTILINE)
    
    for m in matches1 + matches2:
        imported_modules.add(m)

# Standard library modules (approximate list)
std_libs = {
    'os', 'sys', 'json', 'datetime', 'time', 're', 'io', 'math', 'hashlib', 'base64', 
    'uuid', 'logging', 'collections', 'functools', 'itertools', 'traceback', 'subprocess',
    'shutil', 'tempfile', 'urllib', 'http', 'socket', 'threading', 'queue', 'abc', 'typing'
}

third_party = imported_modules - std_libs
# Remove local modules
local_modules = {'app', 'main', 'config'}
third_party = third_party - local_modules

print("Detected imported modules:", third_party)

# Read requirements.txt
with open('requirements.txt', 'r') as req:
    reqs = req.read().lower()

missing = []
for module in sorted(third_party):
    # Mapping modules to package names
    pkg = module.lower()
    if pkg == 'flask_sqlalchemy':
        pkg = 'flask-sqlalchemy'
    elif pkg == 'flask_wtf':
        pkg = 'flask-wtf'
    elif pkg == 'flask_login':
        pkg = 'flask-login'
    elif pkg == 'google':
        pkg = 'google-genai'
    elif pkg == 'dotenv':
        pkg = 'python-dotenv'
        
    # Check if package name is in requirements.txt
    if pkg not in reqs:
        missing.append((module, pkg))

print("\nMissing packages in requirements.txt:")
for m, p in missing:
    print(f"- {m} (package: {p})")
