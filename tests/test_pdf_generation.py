import pytest
import sys
from unittest.mock import MagicMock

# Mock weasyprint for local testing if external binary dependencies are missing
mock_weasyprint = MagicMock()
mock_html = MagicMock()
mock_html.return_value.write_pdf.return_value = b"%PDF-1.4 mock content"
mock_weasyprint.HTML = mock_html
mock_weasyprint.CSS = MagicMock()
sys.modules['weasyprint'] = mock_weasyprint

mock_text_fonts = MagicMock()
mock_text_fonts.FontConfiguration = MagicMock()
sys.modules['weasyprint.text.fonts'] = mock_text_fonts

from app import create_app
from app.models import db, User
import json

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            if not User.query.filter_by(email="test@example.com").first():
                user = User(email="test@example.com", username="testuser")
                user.set_password("password")
                db.session.add(user)
                db.session.commit()
        yield client

def test_pdf_generation_success(client):
    client.post('/auth/login', data={'email': 'test@example.com', 'password': 'password'})
    
    payload = {
        "html": "<h1>Resume Test</h1><p>Education: University</p><p>Skills: Python</p>",
        "name": "Test User",
        "theme": "classic"
    }
    
    response = client.post('/resume-analyzer/export-pdf', 
                           data=json.dumps(payload),
                           content_type='application/json')
    
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/pdf'
    assert int(response.headers['Content-Length']) > 0
    # PDF is not empty and file size > 0

def test_pdf_generation_validation_failure(client):
    client.post('/auth/login', data={'email': 'test@example.com', 'password': 'password'})
    
    payload = {
        # Missing html
        "name": "Test User"
    }
    
    response = client.post('/resume-analyzer/export-pdf', 
                           data=json.dumps(payload),
                           content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
