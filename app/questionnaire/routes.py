"""
Questionnaire management routes
"""
import json
from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, current_app, jsonify, abort
from flask_login import login_required, current_user
from sqlalchemy import desc
from app import db
from app.questionnaire import bp
from app.questionnaire.forms import QuestionnaireForm, QuestionnaireSettingsForm
from app.models import Questionnaire, Question, Response, Answer

@bp.route('/list')
def list_questionnaires():
    """List all accessible questionnaires."""
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('QUESTIONNAIRES_PER_PAGE', 10)
    
    if current_user.is_authenticated:
        if current_user.is_admin():
            # Admin sees all questionnaires
            questionnaires = Questionnaire.query.filter_by(is_active=True)
        else:
            # Regular users see public + their own
            public_filter = (Questionnaire.is_public == True) | \
                           (Questionnaire.creator_id == current_user.id)
            questionnaires = Questionnaire.query.filter(
                Questionnaire.is_active == True,
                public_filter
            )
    else:
        # Anonymous users see only public questionnaires
        questionnaires = Questionnaire.query.filter_by(is_active=True, is_public=True)
    
    questionnaires = questionnaires.order_by(desc(Questionnaire.updated_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('questionnaire/list.html', title='Questionnaires',
                         questionnaires=questionnaires)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create new questionnaire."""
    if not current_user.is_creator():
        flash('You do not have permission to create questionnaires.', 'error')
        return redirect(url_for('main.dashboard'))
    
    form = QuestionnaireForm()
    if form.validate_on_submit():
        questionnaire = Questionnaire(
            title=form.title.data,
            description=form.description.data,
            creator_id=current_user.id,
            is_public=form.is_public.data,
            allow_anonymous=form.allow_anonymous.data,
            allow_multiple_responses=form.allow_multiple_responses.data
        )
        
        db.session.add(questionnaire)
        db.session.commit()
        
        current_app.logger.info(f'Questionnaire created: {questionnaire.title} by {current_user.username}')
        flash('Questionnaire created successfully! Now add some questions.', 'success')
        return redirect(url_for('questionnaire.edit', id=questionnaire.id))
    
    return render_template('questionnaire/create.html', title='Create Questionnaire', form=form)

@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Edit questionnaire."""
    questionnaire = Questionnaire.query.get_or_404(id)
    
    if not current_user.can_edit_questionnaire(questionnaire):
        flash('You do not have permission to edit this questionnaire.', 'error')
        return redirect(url_for('questionnaire.view', id=id))
    
    questions = questionnaire.get_questions()
    
    return render_template('questionnaire/edit.html', 
                         title=f'Edit: {questionnaire.title}',
                         questionnaire=questionnaire,
                         questions=questions)

@bp.route('/view/<int:id>')
def view(id):
    """View questionnaire details."""
    questionnaire = Questionnaire.query.get_or_404(id)
    
    # Check access permissions
    if current_user.is_authenticated:
        if not current_user.can_access_questionnaire(questionnaire):
            abort(403)
    else:
        if not questionnaire.is_public:
            abort(403)
    
    questions = questionnaire.get_questions()
    stats = questionnaire.get_statistics()
    
    # Check if current user has responded
    user_response = None
    if current_user.is_authenticated:
        user_response = Response.query.filter_by(
            questionnaire_id=questionnaire.id,
            user_id=current_user.id,
            is_complete=True
        ).first()
    
    return render_template('questionnaire/view.html',
                         title=questionnaire.title,
                         questionnaire=questionnaire,
                         questions=questions,
                         stats=stats,
                         user_response=user_response)

@bp.route('/respond/<int:id>', methods=['GET', 'POST'])
def respond(id):
    """Respond to questionnaire."""
    questionnaire = Questionnaire.query.get_or_404(id)
    
    # Check if questionnaire is active and accessible
    if not questionnaire.is_active:
        flash('This questionnaire is not currently active.', 'error')
        return redirect(url_for('questionnaire.view', id=id))
    
    # Check access permissions
    user = current_user if current_user.is_authenticated else None
    if not questionnaire.can_user_respond(user):
        if not user and not questionnaire.allow_anonymous:
            flash('You must be logged in to respond to this questionnaire.', 'error')
            return redirect(url_for('auth.login'))
        elif user and not questionnaire.allow_multiple_responses and questionnaire.user_has_responded(user.id):
            flash('You have already responded to this questionnaire.', 'error')
            return redirect(url_for('questionnaire.view', id=id))
        else:
            flash('You cannot respond to this questionnaire.', 'error')
            return redirect(url_for('questionnaire.view', id=id))
    
    questions = questionnaire.get_questions()
    
    # Handle form submission
    if request.method == 'POST':
        # Create or get existing draft response
        response = None
        if user:
            response = Response.query.filter_by(
                questionnaire_id=questionnaire.id,
                user_id=user.id,
                is_complete=False
            ).first()
        
        if not response:
            response = Response(
                questionnaire_id=questionnaire.id,
                user_id=user.id if user else None,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')
            )
            db.session.add(response)
            db.session.flush()  # Get the ID
        
        # Process answers
        valid_submission = True
        for question in questions:
            field_name = f'question_{question.id}'
            answer_value = request.form.get(field_name)
            
            # Check required fields
            if question.is_required and not answer_value:
                flash(f'Question "{question.question_text}" is required.', 'error')
                valid_submission = False
                continue
            
            if answer_value:
                # Get or create answer
                answer = Answer.query.filter_by(
                    response_id=response.id,
                    question_id=question.id
                ).first()
                
                if not answer:
                    answer = Answer(
                        response_id=response.id,
                        question_id=question.id
                    )
                    db.session.add(answer)
                
                # Handle multiple choice (checkbox values)
                if question.question_type == 'multiple_choice':
                    selected_options = request.form.getlist(field_name)
                    answer_value = ', '.join(selected_options)
                
                # Set answer value based on question type
                answer.set_value(answer_value, question.question_type)
        
        if valid_submission:
            # Check if this is a draft save or final submission
            if 'save_draft' in request.form:
                response.is_complete = False
                db.session.commit()
                flash('Your draft has been saved.', 'success')
            else:
                response.is_complete = True
                response.submitted_at = datetime.utcnow()
                db.session.commit()
                
                current_app.logger.info(f'Response submitted for questionnaire {questionnaire.id} by {"user " + str(user.id) if user else "anonymous"}')
                flash('Your response has been submitted successfully!', 'success')
                return redirect(url_for('questionnaire.view', id=id))
        else:
            # Don't save invalid submission
            db.session.rollback()
    
    # Load existing draft if available
    existing_answers = {}
    if user:
        draft_response = Response.query.filter_by(
            questionnaire_id=questionnaire.id,
            user_id=user.id,
            is_complete=False
        ).first()
        
        if draft_response:
            for answer in draft_response.answers:
                existing_answers[answer.question_id] = answer
    
    return render_template('questionnaire/respond.html',
                         title=f'Respond: {questionnaire.title}',
                         questionnaire=questionnaire,
                         questions=questions,
                         existing_answers=existing_answers)

@bp.route('/responses/<int:id>')
@login_required
def responses(id):
    """View questionnaire responses."""
    questionnaire = Questionnaire.query.get_or_404(id)
    
    if not current_user.can_edit_questionnaire(questionnaire):
        flash('You do not have permission to view responses for this questionnaire.', 'error')
        return redirect(url_for('questionnaire.view', id=id))
    
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('RESPONSES_PER_PAGE', 20)
    
    responses = Response.query.filter_by(
        questionnaire_id=questionnaire.id,
        is_complete=True
    ).order_by(desc(Response.submitted_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('questionnaire/responses.html',
                         title=f'Responses: {questionnaire.title}',
                         questionnaire=questionnaire,
                         responses=responses)

@bp.route('/analytics/<int:id>')
@login_required
def analytics(id):
    """View questionnaire analytics."""
    questionnaire = Questionnaire.query.get_or_404(id)
    
    if not current_user.can_edit_questionnaire(questionnaire):
        flash('You do not have permission to view analytics for this questionnaire.', 'error')
        return redirect(url_for('questionnaire.view', id=id))
    
    questions = questionnaire.get_questions()
    
    # Get analytics data for each question
    analytics_data = {}
    for question in questions:
        analytics_data[question.id] = question.get_answer_statistics()
    
    stats = questionnaire.get_statistics()
    
    return render_template('questionnaire/analytics.html',
                         title=f'Analytics: {questionnaire.title}',
                         questionnaire=questionnaire,
                         questions=questions,
                         analytics_data=analytics_data,
                         stats=stats)

@bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    """Delete questionnaire."""
    questionnaire = Questionnaire.query.get_or_404(id)
    
    if not current_user.can_edit_questionnaire(questionnaire):
        flash('You do not have permission to delete this questionnaire.', 'error')
        return redirect(url_for('questionnaire.view', id=id))
    
    title = questionnaire.title
    db.session.delete(questionnaire)
    db.session.commit()
    
    current_app.logger.info(f'Questionnaire deleted: {title} by {current_user.username}')
    flash(f'Questionnaire "{title}" has been deleted.', 'success')
    return redirect(url_for('main.dashboard'))

@bp.route('/settings/<int:id>', methods=['GET', 'POST'])
@login_required
def settings(id):
    """Edit questionnaire settings."""
    questionnaire = Questionnaire.query.get_or_404(id)
    
    if not current_user.can_edit_questionnaire(questionnaire):
        flash('You do not have permission to edit this questionnaire.', 'error')
        return redirect(url_for('questionnaire.view', id=id))
    
    form = QuestionnaireSettingsForm()
    
    if form.validate_on_submit():
        questionnaire.is_active = form.is_active.data
        questionnaire.is_public = form.is_public.data
        questionnaire.allow_anonymous = form.allow_anonymous.data
        questionnaire.allow_multiple_responses = form.allow_multiple_responses.data
        questionnaire.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        current_app.logger.info(f'Questionnaire settings updated: {questionnaire.title} by {current_user.username}')
        flash('Settings updated successfully.', 'success')
        return redirect(url_for('questionnaire.view', id=id))
    
    elif request.method == 'GET':
        form.is_active.data = questionnaire.is_active
        form.is_public.data = questionnaire.is_public
        form.allow_anonymous.data = questionnaire.allow_anonymous
        form.allow_multiple_responses.data = questionnaire.allow_multiple_responses
    
    return render_template('questionnaire/settings.html',
                         title=f'Settings: {questionnaire.title}',
                         questionnaire=questionnaire,
                         form=form)