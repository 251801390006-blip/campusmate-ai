import sqlite3
import json

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

try:
    cursor.execute("SELECT id, user_id, title, theme, content_json FROM user_resumes;")
    rows = cursor.fetchall()
    print("Resumes count:", len(rows))
    for r in rows:
        print(f"ID: {r[0]}, User ID: {r[1]}, Title: {r[2]}, Theme: {r[3]}")
        content = json.loads(r[4])
        print("Keys:", list(content.keys()))
except Exception as e:
    print("Error:", e)

conn.close()
