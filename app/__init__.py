import os
from datetime import timedelta
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager

# Initialize extensions
csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

def create_app():
    app = Flask(__name__)
    
    # Configuration
    secret_key = os.environ.get('SECRET_KEY', 'dev_secret_key_campusmate_ai_99182312')
    app.config['SECRET_KEY'] = secret_key
    
    # Configure database
    db_url = os.environ.get('DATABASE_URL', 'sqlite:///../database.db')
    # Handle postgres:// vs postgresql:// compatibility in production
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Security: Session timeout set to 24 hours
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
    app.config['SESSION_COOKIE_SECURE'] = True if os.environ.get('DATABASE_URL') else False
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    # Initialize extensions with app context
    from app.models import db, User, FeedbackItem
    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
        
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.feedback import feedback_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.features import features_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp)
    app.register_blueprint(feedback_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(features_bp)

    
    # Configure Security Headers via after_request hook
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        # Flexible CSP allowing standard styling & font elements loaded in templates
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self';"
        )
        return response
        
    # Create tables and seed default accounts
    with app.app_context():
        db.create_all()
        # Safe SQLite migrations for User table expansion
        for col, col_type in [
            ("branch", "VARCHAR(100)"),
            ("year", "VARCHAR(20)"),
            ("career_goal", "VARCHAR(100)"),
            ("interests", "TEXT"),
            ("daily_study_time", "VARCHAR(50)"),
            ("xp", "INTEGER DEFAULT 0"),
            ("learning_streak", "INTEGER DEFAULT 0"),
            ("skills", "TEXT"),
            ("onboarded", "BOOLEAN DEFAULT 0"),
            ("name", "VARCHAR(100)"),
            ("avatar", "VARCHAR(200) DEFAULT 'avatar-1.png'"),
            ("bio", "TEXT")
        ]:
            try:
                db.session.execute(db.text(f"ALTER TABLE users ADD COLUMN {col} {col_type}"))
                db.session.commit()
            except Exception:
                db.session.rollback()
        seed_default_users(db, User)
        
    # Global context processor for notifications
    @app.context_processor
    def inject_notifications():
        from flask_login import current_user
        if current_user and current_user.is_authenticated:
            from app.models import Notification
            unread_notifs = Notification.query.filter_by(user_id=current_user.id, is_read=False).order_by(Notification.created_at.desc()).all()
            if not Notification.query.filter_by(user_id=current_user.id).first():
                try:
                    notif1 = Notification(
                        user_id=current_user.id, 
                        title="Welcome to CampusMate AI 🚀", 
                        content="Get started by configuring your onboarding profile to calculate your placement readiness score.", 
                        category="milestone"
                    )
                    notif2 = Notification(
                        user_id=current_user.id, 
                        title="Roadmap Seeding Enabled 🎯", 
                        content="Choose a track in the Roadmap Engine to generate a visual career path with 200 checkpoints.", 
                        category="milestone"
                    )
                    db.session.add_all([notif1, notif2])
                    db.session.commit()
                    unread_notifs = [notif1, notif2]
                except Exception:
                    db.session.rollback()
            return {
                'unread_notifications': unread_notifs,
                'unread_notifications_count': len(unread_notifs)
            }
        return {
            'unread_notifications': [],
            'unread_notifications_count': 0
        }

    return app


def seed_default_users(db, User):
    # Seed default admin user if not exists
    admin = User.query.filter_by(email='251801390006@cutmap.ac.in').first()
    if not admin:
        admin_user = User(
            username='admin',
            email='251801390006@cutmap.ac.in',
            role='admin',
            is_active=True
        )
        admin_user.set_password('Vanjith@2008')
        db.session.add(admin_user)
    else:
        admin.role = 'admin'
        admin.set_password('Vanjith@2008')
        
    # Seed default demo user if not exists
    demo = User.query.filter_by(email='demo@university.edu').first()
    if not demo:
        demo_user = User(
            username='demo',
            email='demo@university.edu',
            role='user',
            is_active=True
        )
        demo_user.set_password('demo1234')
        db.session.add(demo_user)
    else:
        demo.set_password('demo1234')
        
    db.session.commit()
