"""
Authentication routes
"""
from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, current_user
from app import db
from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm, EditProfileForm
from app.models import User

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'error')
            current_app.logger.warning(f'Failed login attempt for username: {form.username.data} from IP: {request.remote_addr}')
            return redirect(url_for('auth.login'))
        
        if not user.is_active:
            flash('Your account has been deactivated. Please contact an administrator.', 'error')
            current_app.logger.warning(f'Login attempt for deactivated user: {user.username} from IP: {request.remote_addr}')
            return redirect(url_for('auth.login'))
        
        # Update last seen
        user.last_seen = datetime.utcnow()
        db.session.commit()
        
        login_user(user, remember=form.remember_me.data)
        current_app.logger.info(f'User {user.username} logged in from IP: {request.remote_addr}')
        
        # Redirect to next page or dashboard
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('main.dashboard')
        return redirect(next_page)
    
    return render_template('auth/login.html', title='Sign In', form=form)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            role=form.role.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        current_app.logger.info(f'New user registered: {user.username} with role: {user.role}')
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', title='Register', form=form)

@bp.route('/logout')
def logout():
    """User logout."""
    if current_user.is_authenticated:
        current_app.logger.info(f'User {current_user.username} logged out')
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@bp.route('/profile')
def profile():
    """User profile page."""
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    
    # Get user statistics
    stats = current_user.get_questionnaire_stats()
    
    return render_template('auth/profile.html', title='Profile', user=current_user, stats=stats)

@bp.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    """Edit user profile."""
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    
    form = EditProfileForm(current_user.username, current_user.email)
    
    if form.validate_on_submit():
        # Check current password if provided
        if form.current_password.data:
            if not current_user.check_password(form.current_password.data):
                flash('Current password is incorrect.', 'error')
                return render_template('auth/edit_profile.html', title='Edit Profile', form=form)
        
        # Update username and email
        current_user.username = form.username.data
        current_user.email = form.email.data
        
        # Update password if provided
        if form.new_password.data:
            if not form.current_password.data:
                flash('Current password is required to change password.', 'error')
                return render_template('auth/edit_profile.html', title='Edit Profile', form=form)
            current_user.set_password(form.new_password.data)
        
        db.session.commit()
        current_app.logger.info(f'User {current_user.username} updated profile')
        flash('Your profile has been updated.', 'success')
        return redirect(url_for('auth.profile'))
    
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    
    return render_template('auth/edit_profile.html', title='Edit Profile', form=form)

@bp.before_app_request
def before_request():
    """Update user's last seen time on each request."""
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()