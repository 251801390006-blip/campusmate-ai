from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from app.models import db, User, FeedbackItem, ResumeAnalysis, RoadmapProgress, UserBadge, UserResume
from app.routes.features import get_predefined_roadmap

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def landing():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))
    return render_template('index.html')

@dashboard_bp.route('/onboarding', methods=['GET', 'POST'])
@login_required
def onboarding():
    if current_user.onboarded:
        return redirect(url_for('dashboard.home'))
        
    from flask import request, flash
    if request.method == 'POST':
        name = request.form.get('name')
        branch = request.form.get('branch')
        year = request.form.get('year')
        career_goal = request.form.get('career_goal')
        interests = request.form.get('interests')
        daily_study_time = request.form.get('daily_study_time')
        skills = request.form.get('skills')
        
        current_user.name = name
        current_user.branch = branch
        current_user.year = year
        current_user.career_goal = career_goal
        current_user.interests = interests
        current_user.daily_study_time = daily_study_time
        current_user.skills = skills
        current_user.onboarded = True
        
        # Initialize an initial empty roadmap for the target career goal
        progress = RoadmapProgress.query.filter_by(user_id=current_user.id).first()
        if not progress:
            new_prog = RoadmapProgress(
                user_id=current_user.id,
                role=career_goal,
                completed_nodes=""
            )
            db.session.add(new_prog)
            
        current_user.xp = 100 # initial gift xp
        current_user.learning_streak = 1
        
        db.session.commit()
        flash("Welcome to CampusMate AI! Your career workspace has been generated.", "success")
        return redirect(url_for('dashboard.home'))
        
    tracks = [
        "Cyber Security", "Ethical Hacking", "SOC Analyst", "Digital Forensics",
        "AI Engineering", "Machine Learning", "Deep Learning", "Generative AI", "Prompt Engineering", "Agentic AI",
        "Data Science", "Data Analytics", "Python Developer", "Java Developer", "C++ Developer",
        "Full Stack Development", "Frontend Development", "Backend Development", "React Developer", "Node.js Developer",
        "Mobile App Development", "Android Development", "Flutter Development",
        "Cloud Computing", "AWS", "Azure", "Google Cloud",
        "DevOps", "Kubernetes", "Docker", "Linux Engineering", "Network Engineering",
        "Blockchain", "Web3", "UI/UX Design", "Product Design", "Product Management",
        "Software Testing", "QA Automation", "Game Development", "AR/VR Development",
        "Robotics", "IoT", "Embedded Systems", "Database Engineering",
        "Site Reliability Engineering", "Business Analysis", "SAP", "Salesforce", "Competitive Programming"
    ]
    return render_template('onboarding.html', tracks=tracks)

@dashboard_bp.route('/dashboard')
@login_required
def home():
    # If standard user is not onboarded, redirect to onboarding wizard
    if not current_user.onboarded and current_user.role != 'admin':
        return redirect(url_for('dashboard.onboarding'))

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
        
    # Calculate Placement Readiness Subscores
    tech_ready = roadmap_percent
    resume_ready = resume_score
    interview_ready = 85 if current_user.xp > 200 else 60
    nodes_completed_count = len(completed_set) if progress else 0
    project_ready = min(100, 40 + nodes_completed_count * 10) if progress else 0
    cert_ready = min(100, 30 + nodes_completed_count * 15) if progress else 0
    
    # Calculate overall score
    total_metrics = [tech_ready, resume_ready, interview_ready, project_ready, cert_ready]
    placement_score = int(sum(total_metrics) / len(total_metrics))
        
    return render_template(
        'dashboard.html',
        total_suggestions=total_suggestions,
        my_tickets_count=my_tickets_count,
        target_role=target_role,
        roadmap_percent=roadmap_percent,
        next_node_title=next_node_title,
        resume_score=resume_score,
        readability_score=readability_score,
        industry_match_score=industry_match_score,
        tech_ready=tech_ready,
        resume_ready=resume_ready,
        interview_ready=interview_ready,
        project_ready=project_ready,
        cert_ready=cert_ready,
        placement_score=placement_score
    )


@dashboard_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        name = request.form.get('name')
        bio = request.form.get('bio')
        skills = request.form.get('skills')
        interests = request.form.get('interests')
        avatar = request.form.get('avatar')
        
        current_user.name = name
        current_user.bio = bio
        current_user.skills = skills
        current_user.interests = interests
        if avatar:
            current_user.avatar = avatar
            
        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for('dashboard.profile'))
        
    badges = UserBadge.query.filter_by(user_id=current_user.id).all()
    resumes = UserResume.query.filter_by(user_id=current_user.id).all()
    
    if not badges:
        badge1 = UserBadge(user_id=current_user.id, badge_name="Quick Starter", badge_icon="fa-rocket")
        badge2 = UserBadge(user_id=current_user.id, badge_name="Streak Maker", badge_icon="fa-fire")
        db.session.add_all([badge1, badge2])
        db.session.commit()
        badges = [badge1, badge2]
        
    return render_template('profile.html', badges=badges, resumes=resumes)


@dashboard_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'password':
            old_pass = request.form.get('old_password')
            new_pass = request.form.get('new_password')
            if current_user.check_password(old_pass):
                current_user.set_password(new_pass)
                db.session.commit()
                flash("Password updated successfully!", "success")
            else:
                flash("Invalid current password entered.", "danger")
        elif action == 'profile':
            name = request.form.get('name')
            bio = request.form.get('bio')
            branch = request.form.get('branch')
            year = request.form.get('year')
            skills = request.form.get('skills')
            goals = request.form.get('goals')
            email = request.form.get('email')
            
            if email:
                existing = User.query.filter(User.email == email, User.id != current_user.id).first()
                if existing:
                    flash("Email address is already in use by another student.", "danger")
                    return redirect(url_for('dashboard.settings'))
                current_user.email = email
                
            current_user.name = name
            current_user.bio = bio
            current_user.branch = branch
            current_user.year = year
            current_user.skills = skills
            current_user.career_goal = goals
            db.session.commit()
            flash("Profile settings updated successfully!", "success")
        else:
            flash("Preferences saved successfully!", "success")
            
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            from flask import jsonify
            return jsonify({"success": True, "message": "Settings updated successfully!"})
        return redirect(url_for('dashboard.settings'))
        
    return render_template('settings.html')


@dashboard_bp.route('/bookmarks')
@login_required
def bookmarks():
    from app.models import SavedItem
    items = SavedItem.query.filter_by(user_id=current_user.id).all()
    
    # Mock seeding if none exist
    if not items:
        item1 = SavedItem(user_id=current_user.id, item_type='roadmap', title=f"{current_user.career_goal or 'AI Engineering'} track roadmap")
        item2 = SavedItem(user_id=current_user.id, item_type='project', title="Hands-on Multi-stage Docker App")
        db.session.add_all([item1, item2])
        db.session.commit()
        items = [item1, item2]
        
    return render_template('bookmarks.html', items=items)


@dashboard_bp.route('/bookmarks/add', methods=['POST'])
@login_required
def add_bookmark():
    from app.models import SavedItem
    item_type = request.form.get('item_type', 'general')
    item_id = request.form.get('item_id')
    title = request.form.get('title', 'Saved Workspace')
    
    existing = SavedItem.query.filter_by(user_id=current_user.id, item_type=item_type, item_id=item_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json or request.args.get('ajax') == '1':
            return jsonify({"success": True, "status": "removed"})
        flash(f"Removed Bookmark: {title}", "info")
    else:
        new_item = SavedItem(user_id=current_user.id, item_type=item_type, item_id=item_id, title=title)
        db.session.add(new_item)
        db.session.commit()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json or request.args.get('ajax') == '1':
            return jsonify({"success": True, "status": "added"})
        flash(f"Bookmarked: {title} successfully!", "success")
    return redirect(request.referrer or url_for('dashboard.bookmarks'))


@dashboard_bp.route('/bookmarks/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_bookmark(item_id):
    from app.models import SavedItem
    item = SavedItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Bookmark removed.", "info")
    return redirect(url_for('dashboard.bookmarks'))


@dashboard_bp.route('/activity-history')
@login_required
def activity_history():
    from app.models import ActivityHistory
    logs = ActivityHistory.query.filter_by(user_id=current_user.id).order_by(ActivityHistory.created_at.desc()).all()
    
    # Mock seed if empty
    if not logs:
        log1 = ActivityHistory(user_id=current_user.id, activity_type='resume', description="Created ATS Resume Version 1.0")
        log2 = ActivityHistory(user_id=current_user.id, activity_type='roadmap', description=f"Initialized target roadmap track to: {current_user.career_goal or 'AI Engineering'}")
        log3 = ActivityHistory(user_id=current_user.id, activity_type='chat', description="Consulted AI Mentor regarding placement preparation strategies")
        db.session.add_all([log1, log2, log3])
        db.session.commit()
        logs = [log1, log2, log3]
        
    return render_template('activity_history.html', logs=logs)


@dashboard_bp.route('/global-search')
@login_required
def global_search():
    from flask import jsonify
    query = request.args.get('q', '').strip().lower()
    if not query:
        return jsonify({"results": []})
    
    # Define searchable platform landmarks
    searchable_items = [
        {"title": "Cyber Security Roadmap", "category": "Roadmap", "url": url_for('features.list_roadmaps') + "?track=Cyber+Security"},
        {"title": "Ethical Hacking Roadmap", "category": "Roadmap", "url": url_for('features.list_roadmaps') + "?track=Ethical+Hacking"},
        {"title": "AI Engineering Roadmap", "category": "Roadmap", "url": url_for('features.list_roadmaps') + "?track=AI+Engineering"},
        {"title": "Machine Learning Roadmap", "category": "Roadmap", "url": url_for('features.list_roadmaps') + "?track=Machine+Learning"},
        {"title": "Full Stack Development Roadmap", "category": "Roadmap", "url": url_for('features.list_roadmaps') + "?track=Full+Stack+Development"},
        {"title": "Resume Builder", "category": "Tool", "url": url_for('features.resume_analyzer')},
        {"title": "AI Interview Simulator", "category": "Tool", "url": url_for('features.interview_prep')},
        {"title": "Internship Command Center", "category": "Tool", "url": url_for('features.internship_center')},
        {"title": "AI Project Architect", "category": "Tool", "url": url_for('features.project_architect')},
        {"title": "Bookmarks & Saved Items Dashboard", "category": "Profile", "url": url_for('dashboard.bookmarks')},
        {"title": "Chronological Activity Timeline", "category": "Profile", "url": url_for('dashboard.activity_history')},
        {"title": "Account Settings & Privacy", "category": "Profile", "url": url_for('dashboard.settings')},
        {"title": "Student Workspace Profile", "category": "Profile", "url": url_for('dashboard.profile')},
        {"title": "Feedback & Support Center", "category": "Collaboration", "url": url_for('feedback.list_feedback')}
    ]
    
    # Add any active user resumes
    resumes = UserResume.query.filter_by(user_id=current_user.id).all()
    for r in resumes:
        searchable_items.append({
            "title": f"Resume: {r.title}",
            "category": "Resume Version",
            "url": url_for('features.resume_analyzer')
        })
        
    results = [item for item in searchable_items if query in item['title'].lower() or query in item['category'].lower()]
    return jsonify({"results": results})


@dashboard_bp.route('/notifications/read/<int:notif_id>', methods=['POST'])
@login_required
def read_notification(notif_id):
    from flask import jsonify
    from app.models import Notification
    notif = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first_or_404()
    notif.is_read = True
    db.session.commit()
    return jsonify({"success": True})


@dashboard_bp.route('/notifications/read-all', methods=['POST'])
@login_required
def read_all_notifications():
    from flask import jsonify
    from app.models import Notification
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({Notification.is_read: True}, synchronize_session=False)
    db.session.commit()
    return jsonify({"success": True})


@dashboard_bp.route('/notifications')
@login_required
def notifications():
    from app.models import Notification
    category_filter = request.args.get('category')
    search_query = request.args.get('q', '').strip()
    
    query = Notification.query.filter_by(user_id=current_user.id)
    
    if category_filter:
        query = query.filter_by(category=category_filter)
        
    if search_query:
        query = query.filter(Notification.title.ilike(f"%{search_query}%") | Notification.content.ilike(f"%{search_query}%"))
        
    notifs = query.order_by(Notification.created_at.desc()).all()
    return render_template('notifications.html', notifications=notifs, category_filter=category_filter, search_query=search_query)


@dashboard_bp.route('/notifications/delete/<int:notif_id>', methods=['POST'])
@login_required
def delete_notification(notif_id):
    from flask import jsonify
    from app.models import Notification
    notif = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first_or_404()
    db.session.delete(notif)
    db.session.commit()
    return jsonify({"success": True})


@dashboard_bp.route('/notifications/delete-all', methods=['POST'])
@login_required
def delete_all_notifications():
    from flask import jsonify
    from app.models import Notification
    Notification.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return jsonify({"success": True})


@dashboard_bp.route('/settings/upload-photo', methods=['POST'])
@login_required
def upload_photo():
    import uuid
    import os
    from werkzeug.utils import secure_filename
    from flask import current_app
    
    if 'profile_photo' not in request.files:
        flash("No file part in request.", "danger")
        return redirect(url_for('dashboard.settings'))
        
    file = request.files['profile_photo']
    if file.filename == '':
        flash("No selected file.", "danger")
        return redirect(url_for('dashboard.settings'))
        
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    
    if ext in allowed_extensions:
        filename = secure_filename(file.filename)
        upload_folder = os.path.join(current_app.root_path, 'static', 'images', 'avatars', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        
        unique_filename = f"{current_user.id}_{uuid.uuid4().hex}.{ext}"
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        
        current_user.profile_photo = f"images/avatars/uploads/{unique_filename}"
        db.session.commit()
        flash("Profile photo updated successfully!", "success")
    else:
        flash("Allowed file types: PNG, JPG, JPEG, GIF", "danger")
        
    return redirect(url_for('dashboard.settings'))


@dashboard_bp.route('/settings/update-preferences', methods=['POST'])
@login_required
def update_preferences():
    public_profile = request.form.get('public_profile') == 'y'
    notifications_enabled = request.form.get('notifications_enabled') == 'y'
    current_user.public_profile = public_profile
    current_user.notifications_enabled = notifications_enabled
    db.session.commit()
    flash("Privacy and notification preferences updated successfully!", "success")
    return redirect(url_for('dashboard.settings'))


@dashboard_bp.route('/settings/export-data', methods=['GET'])
@login_required
def export_data():
    from flask import jsonify
    resumes = UserResume.query.filter_by(user_id=current_user.id).all()
    progress = RoadmapProgress.query.filter_by(user_id=current_user.id).first()
    
    data = {
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "name": current_user.name,
        "bio": current_user.bio,
        "branch": current_user.branch,
        "year": current_user.year,
        "career_goal": current_user.career_goal,
        "interests": current_user.interests,
        "daily_study_time": current_user.daily_study_time,
        "skills": current_user.skills,
        "xp": current_user.xp,
        "learning_streak": current_user.learning_streak,
        "resumes": [
            {
                "title": r.title,
                "theme": r.theme,
                "content": r.content_json,
                "ats_score": r.ats_score,
                "created_at": r.created_at.isoformat()
            } for r in resumes
        ],
        "roadmap": {
            "track": progress.role if progress else None,
            "completed_checkpoints": progress.completed_nodes if progress else ""
        }
    }
    return jsonify(data)


@dashboard_bp.route('/settings/delete-account', methods=['POST'])
@login_required
def delete_account():
    from flask_login import logout_user
    user = User.query.get(current_user.id)
    logout_user()
    db.session.delete(user)
    db.session.commit()
    flash("Your account has been deleted.", "info")
    return redirect(url_for('dashboard.landing'))



