import py_compile
import glob
import os

print("Starting recursive compilation check...")
err_count = 0
for root, dirs, files in os.walk('.'):
    if '.venv' in root or '.git' in root:
        continue
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            try:
                py_compile.compile(filepath, doraise=True)
                print(f"[OK] {filepath}")
            except Exception as e:
                print(f"[FAIL] {filepath}: {e}")
                err_count += 1

if err_count > 0:
    print(f"Compilation finished. Found {err_count} errors.")
else:
    print("All python files compiled successfully!")
