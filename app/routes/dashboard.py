from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from app.models import db, User, FeedbackItem, ResumeAnalysis, RoadmapProgress
from app.routes.features import get_predefined_roadmap

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def landing():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))
    return render_template('index.html')

@dashboard_bp.route('/dashboard')
@login_required
def home():
    # Gather statistics for dashboard widgets
    total_suggestions = FeedbackItem.query.filter_by(is_public=True).count()
    if current_user.role == 'admin':
        my_tickets_count = FeedbackItem.query.filter_by(is_public=False).count()
    else:
        my_tickets_count = FeedbackItem.query.filter_by(is_public=False, user_id=current_user.id).count()
        
    # Get active roadmap details
    progress = RoadmapProgress.query.filter_by(user_id=current_user.id).first()
    target_role = "Not Configured"
    roadmap_percent = 0
    next_node_title = "Select a track in the Roadmap Engine!"
    
    if progress:
        target_role = progress.role
        nodes = get_predefined_roadmap(target_role)
        completed_set = {int(x) for x in progress.completed_nodes.split(",") if x.strip()}
        completed_count = len([n for i, n in enumerate(nodes) if (i+1) in completed_set])
        if nodes:
            roadmap_percent = int((completed_count / len(nodes)) * 100)
            
        # Find first incomplete node
        next_node = None
        for i, n in enumerate(nodes):
            if (i+1) not in completed_set:
                next_node = n
                break
        if next_node:
            next_node_title = next_node['title']
        else:
            next_node_title = "Pathway fully completed! 🎉"
            
    # Get latest resume details
    latest_resume = ResumeAnalysis.query.filter_by(user_id=current_user.id).order_by(ResumeAnalysis.created_at.desc()).first()
    resume_score = 0
    readability_score = 0
    industry_match_score = 0
    if latest_resume:
        resume_score = latest_resume.ats_score
        readability_score = latest_resume.readability_score
        industry_match_score = latest_resume.industry_match_score
        
    return render_template(
        'dashboard.html',
        total_suggestions=total_suggestions,
        my_tickets_count=my_tickets_count,
        target_role=target_role,
        roadmap_percent=roadmap_percent,
        next_node_title=next_node_title,
        resume_score=resume_score,
        readability_score=readability_score,
        industry_match_score=industry_match_score
    )
