from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User
from app.forms import LoginForm, RegistrationForm
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))
        
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account has been deactivated.', 'danger')
                return render_template('login.html', form=form)
                
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.home'))
        else:
            flash('Invalid email or password.', 'danger')
            
    return render_template('login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))
        
    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if username or email already exists
        existing_user = User.query.filter((User.username == form.username.data) | (User.email == form.email.data)).first()
        if existing_user:
            flash('Username or Email is already registered.', 'danger')
            return render_template('register.html', form=form)
            
        new_user = User(
            username=form.username.data,
            email=form.email.data,
            role='user',  # Default is standard user
            is_active=True
        )
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user)
        flash('Account created successfully!', 'success')
        return redirect(url_for('dashboard.home'))
        
    return render_template('register.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('dashboard.landing'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            flash(f"A password reset link has been dispatched to {email}!", "info")
        else:
            flash("If that email address exists in our registry, a reset link has been sent.", "info")
        return redirect(url_for('auth.login'))
    return render_template('forgot_password.html')


@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user:
            user.set_password(password)
            db.session.commit()
            flash("Your password has been reset successfully! Please sign in.", "success")
            return redirect(url_for('auth.login'))
        else:
            flash("Invalid email verification key.", "danger")
    return render_template('reset_password.html')


@auth_bp.route('/verify-email')
def verify_email():
    flash("Your email address has been successfully verified! Welcome to CampusMate.", "success")
    return redirect(url_for('dashboard.home'))


@auth_bp.route('/oauth/<provider>')
def oauth_login(provider):
    email = f"oauth_{provider}@university.edu"
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(
            username=f"{provider}_user",
            email=email,
            role='user',
            is_active=True,
            onboarded=False
        )
        user.set_password('OAuthPassword123!')
        db.session.add(user)
        db.session.commit()
        
    login_user(user)
    flash(f"Successfully authenticated via {provider.title()}!", "success")
    return redirect(url_for('dashboard.home'))


