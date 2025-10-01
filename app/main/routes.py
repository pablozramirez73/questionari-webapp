"""
Main application routes
"""
from flask import render_template, redirect, url_for, request, current_app
from flask_login import current_user, login_required
from sqlalchemy import desc
from app import db
from app.main import bp
from app.models import User, Questionnaire, Response

@bp.route('/')
@bp.route('/index')
def index():
    """Home page."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    # Get public statistics for anonymous users
    stats = {
        'total_questionnaires': Questionnaire.query.filter_by(is_active=True, is_public=True).count(),
        'total_responses': Response.query.filter_by(is_complete=True).count(),
        'total_users': User.query.filter_by(is_active=True).count()
    }
    
    # Get recent public questionnaires
    recent_questionnaires = Questionnaire.query.filter_by(
        is_active=True, 
        is_public=True
    ).order_by(desc(Questionnaire.created_at)).limit(5).all()
    
    return render_template('main/index.html', title='Welcome', stats=stats, 
                         recent_questionnaires=recent_questionnaires)

@bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard."""
    # Get user statistics
    user_stats = current_user.get_questionnaire_stats()
    
    # Get recent questionnaires created by user
    user_questionnaires = current_user.questionnaires.filter_by(
        is_active=True
    ).order_by(desc(Questionnaire.updated_at)).limit(5).all()
    
    # Get recent responses by user
    user_responses = current_user.responses.filter_by(
        is_complete=True
    ).order_by(desc(Response.submitted_at)).limit(5).all()
    
    # Get public questionnaires available to respond to
    available_questionnaires = []
    if current_user.role != 'admin':
        questionnaires = Questionnaire.query.filter_by(
            is_active=True,
            is_public=True
        ).order_by(desc(Questionnaire.created_at)).limit(10).all()
        
        # Filter out questionnaires user has already responded to
        for q in questionnaires:
            if q.can_user_respond(current_user):
                available_questionnaires.append(q)
    
    # Admin gets all questionnaires
    if current_user.is_admin():
        available_questionnaires = Questionnaire.query.filter_by(
            is_active=True
        ).order_by(desc(Questionnaire.created_at)).limit(10).all()
    
    # System statistics for admins
    system_stats = {}
    if current_user.is_admin():
        system_stats = {
            'total_users': User.query.count(),
            'active_users': User.query.filter_by(is_active=True).count(),
            'total_questionnaires': Questionnaire.query.count(),
            'active_questionnaires': Questionnaire.query.filter_by(is_active=True).count(),
            'total_responses': Response.query.count(),
            'complete_responses': Response.query.filter_by(is_complete=True).count()
        }
    
    return render_template('main/dashboard.html', title='Dashboard',
                         user_stats=user_stats,
                         user_questionnaires=user_questionnaires,
                         user_responses=user_responses,
                         available_questionnaires=available_questionnaires,
                         system_stats=system_stats)

@bp.route('/about')
def about():
    """About page."""
    return render_template('main/about.html', title='About')

@bp.route('/search')
def search():
    """Search questionnaires."""
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('QUESTIONNAIRES_PER_PAGE', 10)
    
    if not query:
        questionnaires = Questionnaire.query.filter_by(is_active=True, is_public=True)
    else:
        # Search in title and description
        search_filter = Questionnaire.title.contains(query) | \
                       Questionnaire.description.contains(query)
        questionnaires = Questionnaire.query.filter(
            search_filter,
            Questionnaire.is_active == True,
            Questionnaire.is_public == True
        )
    
    # If user is authenticated, include their private questionnaires
    if current_user.is_authenticated:
        if current_user.is_admin():
            # Admin sees all questionnaires
            if not query:
                questionnaires = Questionnaire.query.filter_by(is_active=True)
            else:
                search_filter = Questionnaire.title.contains(query) | \
                               Questionnaire.description.contains(query)
                questionnaires = Questionnaire.query.filter(
                    search_filter,
                    Questionnaire.is_active == True
                )
        else:
            # Regular users see public + their own
            if query:
                search_filter = Questionnaire.title.contains(query) | \
                               Questionnaire.description.contains(query)
                public_filter = (Questionnaire.is_public == True) | \
                               (Questionnaire.creator_id == current_user.id)
                questionnaires = Questionnaire.query.filter(
                    search_filter,
                    Questionnaire.is_active == True,
                    public_filter
                )
            else:
                public_filter = (Questionnaire.is_public == True) | \
                               (Questionnaire.creator_id == current_user.id)
                questionnaires = Questionnaire.query.filter(
                    Questionnaire.is_active == True,
                    public_filter
                )
    
    questionnaires = questionnaires.order_by(desc(Questionnaire.updated_at))
    
    # Paginate results
    questionnaires = questionnaires.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('main/search.html', title='Search Questionnaires',
                         questionnaires=questionnaires, query=query)