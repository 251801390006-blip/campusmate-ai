from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from app.models import db, User, FeedbackItem

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
        
    return render_template(
        'dashboard.html',
        total_suggestions=total_suggestions,
        my_tickets_count=my_tickets_count
    )
