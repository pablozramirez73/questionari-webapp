"""
Admin routes
"""
import os
from datetime import datetime, timedelta
from flask import render_template, request, current_app, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import desc, func
from app import db
from app.admin import bp
from app.models import User, Questionnaire, Response

def admin_required(f):
    """Decorator for admin-only routes."""
    from functools import wraps
    @wraps(f)
    def admin_wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Admin access required.', 'error')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return admin_wrapper

@bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Admin dashboard."""
    # Get system statistics
    stats = {
        'total_users': User.query.count(),
        'active_users': User.query.filter_by(is_active=True).count(),
        'total_questionnaires': Questionnaire.query.count(),
        'active_questionnaires': Questionnaire.query.filter_by(is_active=True).count(),
        'public_questionnaires': Questionnaire.query.filter_by(is_public=True, is_active=True).count(),
        'total_responses': Response.query.count(),
        'complete_responses': Response.query.filter_by(is_complete=True).count(),
    }
    
    # Get recent activity
    recent_users = User.query.order_by(desc(User.created_at)).limit(5).all()
    recent_questionnaires = Questionnaire.query.order_by(desc(Questionnaire.created_at)).limit(5).all()
    recent_responses = Response.query.filter_by(is_complete=True).order_by(desc(Response.submitted_at)).limit(10).all()
    
    # Get growth statistics (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    growth_stats = {
        'new_users': User.query.filter(User.created_at >= thirty_days_ago).count(),
        'new_questionnaires': Questionnaire.query.filter(Questionnaire.created_at >= thirty_days_ago).count(),
        'new_responses': Response.query.filter(
            Response.submitted_at >= thirty_days_ago,
            Response.is_complete == True
        ).count()
    }
    
    # Get top creators
    top_creators = db.session.query(
        User.username,
        User.id,
        func.count(Questionnaire.id).label('questionnaire_count')
    ).join(Questionnaire, User.id == Questionnaire.creator_id)\
     .group_by(User.id, User.username)\
     .order_by(desc('questionnaire_count'))\
     .limit(5).all()
    
    return render_template('admin/dashboard.html',
                         title='Admin Dashboard',
                         stats=stats,
                         growth_stats=growth_stats,
                         recent_users=recent_users,
                         recent_questionnaires=recent_questionnaires,
                         recent_responses=recent_responses,
                         top_creators=top_creators)

@bp.route('/users')
@login_required
@admin_required
def users():
    """Manage users."""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Filter options
    role_filter = request.args.get('role')
    status_filter = request.args.get('status')
    search = request.args.get('search', '').strip()
    
    query = User.query
    
    if role_filter:
        query = query.filter_by(role=role_filter)
    
    if status_filter == 'active':
        query = query.filter_by(is_active=True)
    elif status_filter == 'inactive':
        query = query.filter_by(is_active=False)
    
    if search:
        search_filter = User.username.contains(search) | User.email.contains(search)
        query = query.filter(search_filter)
    
    users = query.order_by(desc(User.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('admin/users.html',
                         title='User Management',
                         users=users,
                         role_filter=role_filter,
                         status_filter=status_filter,
                         search=search)

@bp.route('/users/<int:user_id>/toggle_status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    """Toggle user active status."""
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'error')
        return redirect(url_for('admin.users'))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'activated' if user.is_active else 'deactivated'
    current_app.logger.info(f'User {user.username} {status} by admin {current_user.username}')
    flash(f'User {user.username} has been {status}.', 'success')
    
    return redirect(url_for('admin.users'))

@bp.route('/users/<int:user_id>/change_role', methods=['POST'])
@login_required
@admin_required
def change_user_role(user_id):
    """Change user role."""
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role')
    
    if new_role not in ['user', 'creator', 'admin']:
        flash('Invalid role specified.', 'error')
        return redirect(url_for('admin.users'))
    
    if user.id == current_user.id and new_role != 'admin':
        flash('You cannot change your own admin role.', 'error')
        return redirect(url_for('admin.users'))
    
    old_role = user.role
    user.role = new_role
    db.session.commit()
    
    current_app.logger.info(f'User {user.username} role changed from {old_role} to {new_role} by admin {current_user.username}')
    flash(f'User {user.username} role changed to {new_role}.', 'success')
    
    return redirect(url_for('admin.users'))

@bp.route('/questionnaires')
@login_required
@admin_required
def questionnaires():
    """Manage questionnaires."""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Filter options
    status_filter = request.args.get('status')
    visibility_filter = request.args.get('visibility')
    search = request.args.get('search', '').strip()
    
    query = Questionnaire.query
    
    if status_filter == 'active':
        query = query.filter_by(is_active=True)
    elif status_filter == 'inactive':
        query = query.filter_by(is_active=False)
    
    if visibility_filter == 'public':
        query = query.filter_by(is_public=True)
    elif visibility_filter == 'private':
        query = query.filter_by(is_public=False)
    
    if search:
        search_filter = Questionnaire.title.contains(search) | \
                       Questionnaire.description.contains(search)
        query = query.filter(search_filter)
    
    questionnaires = query.order_by(desc(Questionnaire.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('admin/questionnaires.html',
                         title='Questionnaire Management',
                         questionnaires=questionnaires,
                         status_filter=status_filter,
                         visibility_filter=visibility_filter,
                         search=search)

@bp.route('/questionnaires/<int:questionnaire_id>/toggle_status', methods=['POST'])
@login_required
@admin_required
def toggle_questionnaire_status(questionnaire_id):
    """Toggle questionnaire active status."""
    questionnaire = Questionnaire.query.get_or_404(questionnaire_id)
    
    questionnaire.is_active = not questionnaire.is_active
    questionnaire.updated_at = datetime.utcnow()
    db.session.commit()
    
    status = 'activated' if questionnaire.is_active else 'deactivated'
    current_app.logger.info(f'Questionnaire {questionnaire.title} {status} by admin {current_user.username}')
    flash(f'Questionnaire "{questionnaire.title}" has been {status}.', 'success')
    
    return redirect(url_for('admin.questionnaires'))

@bp.route('/logs')
@login_required
@admin_required
def logs():
    """View system logs."""
    log_file = 'logs/questionnaire_app.log'
    log_lines = []
    
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r') as f:
                # Get last 100 lines
                lines = f.readlines()
                log_lines = lines[-100:] if len(lines) > 100 else lines
                log_lines.reverse()  # Show newest first
        except Exception as e:
            flash(f'Error reading log file: {str(e)}', 'error')
    else:
        flash('Log file not found.', 'warning')
    
    return render_template('admin/logs.html',
                         title='System Logs',
                         log_lines=log_lines)

@bp.route('/system_info')
@login_required
@admin_required
def system_info():
    """View system information."""
    import sys
    import platform
    from flask import __version__ as flask_version
    
    system_info = {
        'python_version': sys.version,
        'flask_version': flask_version,
        'platform': platform.platform(),
        'database_url': current_app.config.get('SQLALCHEMY_DATABASE_URI', '').split('/')[-1],
        'debug_mode': current_app.debug,
        'secret_key_set': bool(current_app.config.get('SECRET_KEY')),
    }
    
    # Database statistics
    try:
        db_stats = {
            'total_tables': len(db.metadata.tables),
            'total_users': User.query.count(),
            'total_questionnaires': Questionnaire.query.count(),
            'total_questions': db.session.query(func.count(db.text('questions.id'))).scalar(),
            'total_responses': Response.query.count(),
            'total_answers': db.session.query(func.count(db.text('answers.id'))).scalar(),
        }
    except Exception as e:
        db_stats = {'error': str(e)}
    
    return render_template('admin/system_info.html',
                         title='System Information',
                         system_info=system_info,
                         db_stats=db_stats)