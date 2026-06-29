import os
from datetime import timedelta
from flask import Flask, render_template, flash, redirect, request, url_for
from flask_wtf.csrf import CSRFProtect, CSRFError
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
    secret_key = os.environ.get('SECRET_KEY', 'campusmate-default-static-key-12345')
    app.config['SECRET_KEY'] = secret_key
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max-limit
    
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
            ("notifications_enabled", "BOOLEAN DEFAULT 1"),
            ("college", "VARCHAR(150)"),
            ("roles", "VARCHAR(200)"),
            ("domains", "VARCHAR(200)")
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
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        flash("Your session expired. Please refresh and try again.", "warning")
        return redirect(request.referrer or url_for('auth.login'))

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
        if Internship.query.count() != 15:
            # Wipe existing generic records and re-seed with 15 specific market internships
            Internship.query.delete()
            db.session.commit()

            # Specific current market internships (Summer/Fall 2026/2027)
            market_internships = [
                {
                    "company_name": "Google", "company_logo": "fa-brands fa-google", "role": "Software Engineering Intern, Summer 2027", 
                    "type": "Summer", "location": "Hybrid", "skills": "C++, Java, Python", "eligibility": "B.Tech/BS in CS (Graduating 2028)",
                    "stipend": "$9,500/mo", "deadline": "2026-10-15", "official_link": "https://www.google.com/about/careers/applications/students/", "is_pinned": True
                },
                {
                    "company_name": "Rivian", "company_logo": "fa-solid fa-car", "role": "Software Engineer Intern, Fall 2026", 
                    "type": "Fall", "location": "Onsite", "skills": "Python, React, AWS", "eligibility": "B.Tech 3rd/4th Year",
                    "stipend": "$8,000/mo", "deadline": "2026-08-01", "official_link": "https://careers.rivian.com/university", "is_pinned": True
                },
                {
                    "company_name": "Databricks", "company_logo": "fa-solid fa-database", "role": "Data Science Intern", 
                    "type": "Summer", "location": "Hybrid", "skills": "SQL, Python, Spark", "eligibility": "MS/PhD in CS or Stats",
                    "stipend": "$10,500/mo", "deadline": "2026-09-30", "official_link": "https://www.databricks.com/company/careers/university", "is_pinned": True
                },
                {
                    "company_name": "Microsoft", "company_logo": "fa-brands fa-microsoft", "role": "Cloud Security Engineering Intern", 
                    "type": "Summer", "location": "Remote", "skills": "Azure, Networking, Python", "eligibility": "B.Tech/M.Tech (Cyber Security)",
                    "stipend": "$8,700/mo", "deadline": "2026-11-01", "official_link": "https://careers.microsoft.com/students/us/en", "is_pinned": False
                },
                {
                    "company_name": "Meta", "company_logo": "fa-brands fa-meta", "role": "AI/ML Research Intern", 
                    "type": "Research", "location": "Onsite", "skills": "PyTorch, Computer Vision", "eligibility": "PhD (AI/ML/CS)",
                    "stipend": "$11,000/mo", "deadline": "2026-10-31", "official_link": "https://www.metacareers.com/students", "is_pinned": False
                },
                {
                    "company_name": "NVIDIA", "company_logo": "fa-solid fa-microchip", "role": "Deep Learning Intern (Autonomous Vehicles)", 
                    "type": "Summer", "location": "Hybrid", "skills": "C++, CUDA, Deep Learning", "eligibility": "M.Tech/PhD",
                    "stipend": "$9,800/mo", "deadline": "2026-09-15", "official_link": "https://www.nvidia.com/en-us/about-nvidia/careers/university-recruiting/", "is_pinned": True
                },
                {
                    "company_name": "Amazon", "company_logo": "fa-brands fa-amazon", "role": "SDE Intern (AWS Core)", 
                    "type": "Summer", "location": "Hybrid", "skills": "Java, Linux, Distributed Systems", "eligibility": "B.Tech 3rd Year",
                    "stipend": "$9,200/mo", "deadline": "2026-12-01", "official_link": "https://www.amazon.jobs/en/landing_pages/interns", "is_pinned": False
                },
                {
                    "company_name": "Netflix", "company_logo": "fa-solid fa-film", "role": "Frontend Engineering Intern", 
                    "type": "Summer", "location": "Remote", "skills": "React, TypeScript, GraphQL", "eligibility": "B.Tech/BS",
                    "stipend": "$10,000/mo", "deadline": "2026-09-20", "official_link": "https://jobs.netflix.com/early-career", "is_pinned": False
                },
                {
                    "company_name": "Apple", "company_logo": "fa-brands fa-apple", "role": "Hardware Engineering Intern", 
                    "type": "Summer", "location": "Onsite", "skills": "Verilog, Circuit Design, C", "eligibility": "B.Tech (ECE/EE)",
                    "stipend": "$8,900/mo", "deadline": "2026-10-10", "official_link": "https://www.apple.com/careers/us/students.html", "is_pinned": False
                },
                {
                    "company_name": "OpenAI", "company_logo": "fa-solid fa-brain", "role": "AI Alignment Intern", 
                    "type": "Research", "location": "Hybrid", "skills": "Python, LLMs, RLHF", "eligibility": "PhD/Post-Doc",
                    "stipend": "$12,000/mo", "deadline": "2026-11-15", "official_link": "https://openai.com/careers/search?department=Research", "is_pinned": True
                },
                {
                    "company_name": "Stripe", "company_logo": "fa-brands fa-stripe", "role": "Backend Software Engineer Intern", 
                    "type": "Summer", "location": "Remote", "skills": "Ruby, Go, API Design", "eligibility": "B.Tech (Graduating 2027/2028)",
                    "stipend": "$9,500/mo", "deadline": "2026-10-01", "official_link": "https://stripe.com/jobs/university", "is_pinned": False
                },
                {
                    "company_name": "CrowdStrike", "company_logo": "fa-solid fa-shield-halved", "role": "Cybersecurity Analyst Intern", 
                    "type": "Summer", "location": "Hybrid", "skills": "SIEM, Python, Network Forensics", "eligibility": "B.Sc/B.Tech (Cyber Security)",
                    "stipend": "$7,800/mo", "deadline": "2026-12-15", "official_link": "https://www.crowdstrike.com/careers/university/", "is_pinned": False
                },
                {
                    "company_name": "Adobe", "company_logo": "fa-solid fa-wand-magic-sparkles", "role": "UI/UX Design Intern", 
                    "type": "Summer", "location": "Remote", "skills": "Figma, Prototyping, User Research", "eligibility": "B.Des/BCA/B.Tech",
                    "stipend": "$7,500/mo", "deadline": "2026-11-20", "official_link": "https://careers.adobe.com/us/en/university", "is_pinned": False
                },
                {
                    "company_name": "Salesforce", "company_logo": "fa-brands fa-salesforce", "role": "Product Management Intern", 
                    "type": "Summer", "location": "Hybrid", "skills": "Agile, Jira, Data Analysis", "eligibility": "MBA/B.Tech",
                    "stipend": "$8,200/mo", "deadline": "2026-10-25", "official_link": "https://salesforce.wd1.myworkdayjobs.com/Futureforce_Internships", "is_pinned": False
                },
                {
                    "company_name": "Simplify", "company_logo": "fa-solid fa-briefcase", "role": "Software Engineer Intern (Off-Cycle)", 
                    "type": "Off-Cycle", "location": "Remote", "skills": "React, Node.js, Next.js", "eligibility": "Any Student",
                    "stipend": "$6,000/mo", "deadline": "2026-08-30", "official_link": "https://simplify.jobs/", "is_pinned": True
                }
            ]

            internships = []
            for item in market_internships:
                internships.append(Internship(
                    company_name=item["company_name"],
                    company_logo=item["company_logo"],
                    role=item["role"],
                    internship_type=item["type"],
                    location_type=item["location"],
                    skills_required=item["skills"],
                    eligibility=item["eligibility"],
                    stipend=item["stipend"],
                    deadline=item["deadline"],
                    official_link=item["official_link"],
                    is_pinned=item["is_pinned"],
                ))

            db.session.add_all(internships)
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error seeding internships: {e}")
