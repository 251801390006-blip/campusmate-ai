import sys
import os
import json

sys.path.insert(0, r"c:\CampusMate AI")

from app import create_app
from app.models import db, User, UserResume

def test_new_themes():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    client = app.test_client()
    
    # Login demo user
    client.post('/auth/login', data={
        'email': 'demo@university.edu',
        'password': 'demo1234'
    }, follow_redirects=True)
    
    test_themes = ["classic", "modern-cyan", "canva-sidebar", "canva-elegant", "canva-split"]
    
    for theme in test_themes:
        print(f"\n--- Testing PDF Export Route for theme: {theme} ---")
        resume_payload = {
            "theme": theme,
            "content": {
                "name": "Alex Test",
                "email": "test@univ.edu",
                "phone": "+123456",
                "address": "Test City",
                "sectionOrder": ["education", "skills", "experience"],
                "education": [
                    {
                        "inst": "Test Univ",
                        "degree": "B.S. Computer Science",
                        "dates": "2024-2028",
                        "gpa": "3.9/4.0",
                        "coursework": "Data Structures, Algorithms"
                    }
                ],
                "skillsProg": "Python, JavaScript",
                "skillsCyber": "Vulnerability assessment",
                "skillsTools": "Docker, Kubernetes",
                "skillsWeb": "React, Flask",
                "experience": [
                    {
                        "role": "Security Intern",
                        "company": "SecureCorp",
                        "dates": "Summer 2025",
                        "bullets": ["Vulnerability scanned software", "Fixed key bugs"]
                    }
                ]
            }
        }
        
        pdf_res = client.post('/resume-analyzer/export-pdf', 
                              data=json.dumps(resume_payload),
                              content_type='application/json')
        print(f"PDF Export status: {pdf_res.status_code}")
        assert pdf_res.status_code == 200
        assert pdf_res.headers.get('Content-Type') == 'application/pdf'
        assert b'%PDF' in pdf_res.data
        print(f"[Success] Theme '{theme}' verified successfully!")

    print("\n--- All New Themes PDF Generation Verified Successfully! ---")

if __name__ == '__main__':
    test_new_themes()
