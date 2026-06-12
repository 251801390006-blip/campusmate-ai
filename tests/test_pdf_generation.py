import pytest
from app import create_app
from app.models import db, User
import json

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
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
