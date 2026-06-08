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

