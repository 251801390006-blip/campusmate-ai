import os
from datetime import timedelta
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager

# Load .env file for local development (ignored in production where env vars are set directly)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


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
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
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
            ("bio", "TEXT"),
            ("profile_photo", "VARCHAR(255)"),
            ("published_portfolio_html", "TEXT"),
            ("public_profile", "BOOLEAN DEFAULT 1"),
            ("notifications_enabled", "BOOLEAN DEFAULT 1")
        ]:
            try:
                db.session.execute(db.text(f"ALTER TABLE users ADD COLUMN {col} {col_type}"))
                db.session.commit()
            except Exception:
                db.session.rollback()
        seed_default_users(db, User)
        seed_default_internships(db)

        
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


def seed_default_internships(db):
    from app.models import Internship
    try:
        if Internship.query.count() < 100:
            # Wipe existing records and re-seed with the full 105-entry set
            Internship.query.delete()
            db.session.commit()

            # --- 15 companies -------------------------------------------------
            companies = [
                {"name": "Google",      "logo": "fa-brands fa-google",              "link": "https://careers.google.com",                              "stipend": "$9,000/mo",  "pinned": True},
                {"name": "Microsoft",   "logo": "fa-brands fa-microsoft",           "link": "https://careers.microsoft.com",                           "stipend": "$8,500/mo",  "pinned": True},
                {"name": "Meta",        "logo": "fa-brands fa-meta",                "link": "https://www.metacareers.com",                             "stipend": "$9,200/mo",  "pinned": False},
                {"name": "Amazon",      "logo": "fa-brands fa-amazon",              "link": "https://www.amazon.jobs",                                 "stipend": "$8,800/mo",  "pinned": False},
                {"name": "Apple",       "logo": "fa-brands fa-apple",               "link": "https://jobs.apple.com",                                  "stipend": "$9,000/mo",  "pinned": False},
                {"name": "NVIDIA",      "logo": "fa-solid fa-microchip",            "link": "https://www.nvidia.com/en-us/about-nvidia/careers/",      "stipend": "$8,200/mo",  "pinned": False},
                {"name": "Netflix",     "logo": "fa-solid fa-film",                 "link": "https://jobs.netflix.com",                                "stipend": "$8,000/mo",  "pinned": False},
                {"name": "OpenAI",      "logo": "fa-solid fa-brain",                "link": "https://openai.com/careers",                              "stipend": "$10,000/mo", "pinned": False},
                {"name": "Stripe",      "logo": "fa-brands fa-stripe",              "link": "https://stripe.com/jobs",                                 "stipend": "$8,500/mo",  "pinned": False},
                {"name": "CrowdStrike", "logo": "fa-solid fa-shield-halved",        "link": "https://www.crowdstrike.com/careers/",                    "stipend": "$7,500/mo",  "pinned": False},
                {"name": "Adobe",       "logo": "fa-solid fa-wand-magic-sparkles",  "link": "https://www.adobe.com/careers.html",                      "stipend": "$7,800/mo",  "pinned": False},
                {"name": "Salesforce",  "logo": "fa-brands fa-salesforce",          "link": "https://www.salesforce.com/company/careers/",             "stipend": "$7,600/mo",  "pinned": False},
                {"name": "Intel",       "logo": "fa-solid fa-memory",               "link": "https://jobs.intel.com",                                  "stipend": "$7,200/mo",  "pinned": False},
                {"name": "IBM",         "logo": "fa-solid fa-server",               "link": "https://www.ibm.com/careers",                             "stipend": "$6,800/mo",  "pinned": False},
                {"name": "Cisco",       "logo": "fa-solid fa-network-wired",        "link": "https://jobs.cisco.com",                                  "stipend": "$7,000/mo",  "pinned": False},
            ]

            # --- 7 roles ------------------------------------------------------
            roles = [
                {"role": "Software Engineer Intern",    "type": "Summer",   "location": "Hybrid",  "skills": "Python, Java, Data Structures, Algorithms",        "eligibility": "B.Tech 3rd/4th Year (CS/IT)"},
                {"role": "Frontend Developer Intern",    "type": "Summer",   "location": "Remote",  "skills": "React, TypeScript, CSS, Figma",                    "eligibility": "B.Tech/BCA (CS/IT/Design)"},
                {"role": "Data Science Intern",          "type": "Summer",   "location": "Onsite",  "skills": "Python, Pandas, SQL, Tableau",                     "eligibility": "B.Tech/M.Tech (CS/Stats/Math)"},
                {"role": "Machine Learning Intern",      "type": "Research", "location": "Hybrid",  "skills": "PyTorch, TensorFlow, NLP, Computer Vision",        "eligibility": "M.Tech/PhD (AI/ML/CS)"},
                {"role": "DevOps/Cloud Intern",          "type": "Summer",   "location": "Remote",  "skills": "AWS/GCP, Docker, Kubernetes, CI/CD",               "eligibility": "B.Tech 3rd/4th Year (CS/IT)"},
                {"role": "Cybersecurity Intern",         "type": "Summer",   "location": "Onsite",  "skills": "Nmap, Wireshark, Linux, SIEM",                     "eligibility": "B.Tech/B.Sc (Cyber Security/CS)"},
                {"role": "Product Management Intern",    "type": "Summer",   "location": "Hybrid",  "skills": "Analytics, Jira, A/B Testing, SQL",                "eligibility": "MBA/B.Tech (Any Branch)"},
            ]

            # Stagger deadlines across Aug-Dec 2026 (months 8-12)
            deadline_months = [8, 9, 10, 11, 12]

            internships = []
            entry_index = 0
            for company in companies:
                for role_info in roles:
                    month = deadline_months[entry_index % len(deadline_months)]
                    day = 1 + (entry_index % 28)  # days 1-28 to stay valid
                    deadline = f"2026-{month:02d}-{day:02d}"

                    internships.append(Internship(
                        company_name=company["name"],
                        company_logo=company["logo"],
                        role=role_info["role"],
                        internship_type=role_info["type"],
                        location_type=role_info["location"],
                        skills_required=role_info["skills"],
                        eligibility=role_info["eligibility"],
                        stipend=company["stipend"],
                        deadline=deadline,
                        official_link=company["link"],
                        is_pinned=company["pinned"],
                    ))
                    entry_index += 1

            db.session.add_all(internships)
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error seeding internships: {e}")
