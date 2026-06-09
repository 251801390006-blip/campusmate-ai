from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user', nullable=False) # 'user' or 'admin'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    plain_password = db.Column(db.String(255), nullable=True)
    
    # Onboarding and gamification properties
    branch = db.Column(db.String(100), nullable=True)
    year = db.Column(db.String(20), nullable=True)
    career_goal = db.Column(db.String(100), nullable=True)
    interests = db.Column(db.Text, nullable=True)
    daily_study_time = db.Column(db.String(50), nullable=True)
    xp = db.Column(db.Integer, default=0, nullable=False)
    learning_streak = db.Column(db.Integer, default=0, nullable=False)
    skills = db.Column(db.Text, nullable=True)
    onboarded = db.Column(db.Boolean, default=False, nullable=False)
    
    # Profile Extensions
    name = db.Column(db.String(100), nullable=True)
    avatar = db.Column(db.String(200), nullable=True, default='avatar-1.png')
    bio = db.Column(db.Text, nullable=True)
    profile_photo = db.Column(db.String(255), nullable=True)
    published_portfolio_html = db.Column(db.Text, nullable=True)
    public_profile = db.Column(db.Boolean, default=True, nullable=False)
    notifications_enabled = db.Column(db.Boolean, default=True, nullable=False)

    
    # Relationships
    feedback_items = db.relationship('FeedbackItem', backref='author', lazy=True, cascade="all, delete-orphan")
    replies = db.relationship('FeedbackReply', backref='author', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        self.plain_password = password
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class FeedbackItem(db.Model):
    __tablename__ = 'feedback_items'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='suggestion', nullable=False) # 'suggestion', 'bug', 'issue', 'feature_request'
    is_public = db.Column(db.Boolean, default=True, nullable=False)
    status = db.Column(db.String(20), default='open', nullable=False) # 'open' or 'resolved'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    replies = db.relationship('FeedbackReply', backref='feedback_item', lazy=True, cascade="all, delete-orphan")

class FeedbackReply(db.Model):
    __tablename__ = 'feedback_replies'
    
    id = db.Column(db.Integer, primary_key=True)
    feedback_item_id = db.Column(db.Integer, db.ForeignKey('feedback_items.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    sender = db.Column(db.String(10), nullable=False) # 'user' or 'ai'
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class ResumeAnalysis(db.Model):
    __tablename__ = 'resume_analyses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    filename = db.Column(db.String(150), nullable=False)
    ats_score = db.Column(db.Integer, nullable=False)
    readability_score = db.Column(db.Integer, nullable=False)
    industry_match_score = db.Column(db.Integer, nullable=False)
    target_role = db.Column(db.String(100), nullable=True)
    analysis_json = db.Column(db.Text, nullable=False) # Serialized JSON of keywords, mistakes, improvements
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class RoadmapProgress(db.Model):
    __tablename__ = 'roadmap_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role = db.Column(db.String(100), nullable=False) # e.g. 'Cyber Security'
    completed_nodes = db.Column(db.Text, default="") # Comma-separated node indices, e.g. "1,2,5"
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class UserResume(db.Model):
    __tablename__ = 'user_resumes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    theme = db.Column(db.String(50), default='classic', nullable=False)
    content_json = db.Column(db.Text, nullable=False) # holds serialized dict
    ats_score = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('resumes', lazy=True, cascade="all, delete-orphan"))


class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='general', nullable=False) # 'milestone', 'cert', 'interview', 'streak', 'achievement'
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('notifications', lazy=True, cascade="all, delete-orphan"))


class SavedItem(db.Model):
    __tablename__ = 'saved_items'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    item_type = db.Column(db.String(50), nullable=False) # 'roadmap', 'cert', 'project', 'resource', 'note'
    item_id = db.Column(db.String(100), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    metadata_json = db.Column(db.Text, nullable=True) # JSON config
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('saved_items', lazy=True, cascade="all, delete-orphan"))


class ActivityHistory(db.Model):
    __tablename__ = 'activity_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False) # 'chat', 'roadmap', 'resume', 'cert', 'project'
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('activities', lazy=True, cascade="all, delete-orphan"))


class UserBadge(db.Model):
    __tablename__ = 'user_badges'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    badge_name = db.Column(db.String(100), nullable=False)
    badge_icon = db.Column(db.String(100), nullable=False) # e.g. 'fa-star', 'fa-fire'
    unlocked_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('badges', lazy=True, cascade="all, delete-orphan"))


class AdminReview(db.Model):
    __tablename__ = 'admin_reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    resume_id = db.Column(db.Integer, db.ForeignKey('user_resumes.id', ondelete='CASCADE'), nullable=True)
    job_id = db.Column(db.Integer, nullable=True) # ID of matched job from features
    status = db.Column(db.String(20), default='pending', nullable=False) # 'pending', 'approved', 'rejected'
    feedback = db.Column(db.Text, nullable=True)
    suggested_improvements = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('admin_reviews', lazy=True, cascade="all, delete-orphan"))
    resume = db.relationship('UserResume', backref=db.backref('reviews', lazy=True, cascade="all, delete-orphan"))


class Internship(db.Model):
    __tablename__ = 'internships'
    
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    company_logo = db.Column(db.String(100), nullable=True, default='fa-solid fa-briefcase')
    role = db.Column(db.String(100), nullable=False)
    internship_type = db.Column(db.String(50), default='Summer') # Summer, Winter, Semester
    location_type = db.Column(db.String(50), default='Remote') # Remote, Hybrid, Onsite
    skills_required = db.Column(db.Text, nullable=True) # Comma-separated skills
    eligibility = db.Column(db.String(200), nullable=True)
    stipend = db.Column(db.String(50), nullable=True)
    deadline = db.Column(db.String(50), nullable=True)
    official_link = db.Column(db.String(255), nullable=True)
    is_pinned = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class SiteConfig(db.Model):
    """
    Stores site-wide admin settings as key-value pairs in the database.
    These persist permanently on the server — independent of any browser/device.
    Example key: 'global_ai_key'  value: 'gsk_xxxx...'
    """
    __tablename__ = 'site_config'

    id    = db.Column(db.Integer, primary_key=True)
    key   = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get(cls, key, default=None):
        """Read a config value by key."""
        row = cls.query.filter_by(key=key).first()
        return row.value if row and row.value else default

    @classmethod
    def set(cls, key, value):
        """Write (upsert) a config value."""
        row = cls.query.filter_by(key=key).first()
        if row:
            row.value = value
            row.updated_at = datetime.utcnow()
        else:
            row = cls(key=key, value=value)
            db.session.add(row)
        db.session.commit()

    @classmethod
    def delete(cls, key):
        """Delete a config key."""
        cls.query.filter_by(key=key).delete()
        db.session.commit()
