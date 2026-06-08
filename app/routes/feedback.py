from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.models import db, User, FeedbackItem, FeedbackReply
from app.forms import FeedbackForm, ReplyForm

feedback_bp = Blueprint('feedback', __name__, url_prefix='/feedback')

@feedback_bp.route('/', methods=['GET', 'POST'])
@login_required
def list_feedback():
    form = FeedbackForm()
    if form.validate_on_submit():
        new_item = FeedbackItem(
            user_id=current_user.id,
            title=form.title.data,
            content=form.content.data,
            category=form.category.data,
            is_public=form.is_public.data,
            status='open'
        )
        db.session.add(new_item)
        db.session.commit()
        flash('Your feedback has been submitted successfully!', 'success')
        return redirect(url_for('feedback.list_feedback'))
        
    # Query public suggestions
    suggestions = FeedbackItem.query.filter_by(is_public=True).order_by(FeedbackItem.created_at.desc()).all()
    
    # Query private tickets
    if current_user.role == 'admin':
        tickets = FeedbackItem.query.filter_by(is_public=False).order_by(FeedbackItem.created_at.desc()).all()
    else:
        tickets = FeedbackItem.query.filter_by(is_public=False, user_id=current_user.id).order_by(FeedbackItem.created_at.desc()).all()
        
    return render_template('feedback.html', form=form, suggestions=suggestions, tickets=tickets)

@feedback_bp.route('/<int:item_id>', methods=['GET', 'POST'])
@login_required
def detail(item_id):
    item = FeedbackItem.query.get_or_404(item_id)
    
    # Access control check
    if not item.is_public:
        if current_user.role != 'admin' and item.user_id != current_user.id:
            abort(403)
            
    reply_form = ReplyForm()
    
    # Check if standard user attempts to reply to a resolved ticket
    can_reply = True
    if item.status == 'resolved' and current_user.role != 'admin':
        can_reply = False
        
    if reply_form.validate_on_submit():
        if not can_reply:
            flash('This ticket is resolved. Standard users cannot reply to resolved tickets.', 'danger')
            return redirect(url_for('feedback.detail', item_id=item.id))
            
        new_reply = FeedbackReply(
            feedback_item_id=item.id,
            user_id=current_user.id,
            content=reply_form.content.data
        )
        db.session.add(new_reply)
        db.session.commit()
        flash('Reply posted successfully.', 'success')
        return redirect(url_for('feedback.detail', item_id=item.id))
        
    replies = FeedbackReply.query.filter_by(feedback_item_id=item.id).order_by(FeedbackReply.created_at.asc()).all()
    return render_template('feedback_detail.html', item=item, replies=replies, reply_form=reply_form, can_reply=can_reply)

@feedback_bp.route('/<int:item_id>/toggle-status', methods=['POST'])
@login_required
def toggle_status(item_id):
    item = FeedbackItem.query.get_or_404(item_id)
    
    # Authorization: only ticket owner or admins can change status
    if current_user.role != 'admin' and item.user_id != current_user.id:
        abort(403)
        
    item.status = 'resolved' if item.status == 'open' else 'open'
    db.session.commit()
    flash(f"Ticket status marked as {item.status.upper()}.", "success")
    return redirect(url_for('feedback.detail', item_id=item.id))
