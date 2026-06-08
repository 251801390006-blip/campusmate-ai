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

# Quick Login Bypass for testing
@auth_bp.route('/switch-account/<role>')
def switch_account(role):
    logout_user()
    
    role = role.lower()
    if role == 'admin':
        username = 'admin'
        email = '251801390006@cutmap.ac.in'
        target_role = 'admin'
        password = 'Vanjith@2008'
    else:
        username = 'demo'
        email = 'demo@university.edu'
        target_role = 'user'
        password = 'demo1234'
        
    # Check if user exists, else seed
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(
            username=username,
            email=email,
            role=target_role,
            is_active=True
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
    user.last_login = datetime.utcnow()
    db.session.commit()
    login_user(user)
    
    flash(f"Switched account to {username.upper()} ({target_role.upper()})!", "success")
    return redirect(url_for('dashboard.home'))
