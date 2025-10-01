"""
API routes for AJAX operations
"""
import json
from flask import jsonify, request, current_app
from flask_login import login_required, current_user
from app import db
from app.api import bp
from app.models import Questionnaire, Question, Response, Answer

@bp.route('/questions/<int:questionnaire_id>', methods=['GET'])
@login_required
def get_questions(questionnaire_id):
    """Get questions for a questionnaire."""
    questionnaire = Questionnaire.query.get_or_404(questionnaire_id)
    
    if not current_user.can_edit_questionnaire(questionnaire):
        return jsonify({'error': 'Permission denied'}), 403
    
    questions = questionnaire.get_questions()
    return jsonify({
        'questions': [q.to_dict() for q in questions]
    })

@bp.route('/questions', methods=['POST'])
@login_required
def create_question():
    """Create new question."""
    data = request.get_json()
    
    questionnaire = Questionnaire.query.get_or_404(data.get('questionnaire_id'))
    
    if not current_user.can_edit_questionnaire(questionnaire):
        return jsonify({'error': 'Permission denied'}), 403
    
    # Get the highest order_index for this questionnaire
    max_order = db.session.query(db.func.max(Question.order_index)).filter_by(
        questionnaire_id=questionnaire.id
    ).scalar() or 0
    
    question = Question(
        questionnaire_id=questionnaire.id,
        question_text=data.get('question_text', ''),
        question_type=data.get('question_type', 'open_ended'),
        is_required=data.get('is_required', False),
        order_index=max_order + 1
    )
    
    # Handle options for choice questions
    if data.get('options') and question.question_type in ['single_choice', 'multiple_choice']:
        options = [opt.strip() for opt in data.get('options', []) if opt.strip()]
        question.options = options
    
    db.session.add(question)
    db.session.commit()
    
    current_app.logger.info(f'Question created for questionnaire {questionnaire.id} by {current_user.username}')
    
    return jsonify({
        'success': True,
        'question': question.to_dict()
    })

@bp.route('/questions/<int:question_id>', methods=['PUT'])
@login_required
def update_question(question_id):
    """Update question."""
    question = Question.query.get_or_404(question_id)
    questionnaire = question.questionnaire
    
    if not current_user.can_edit_questionnaire(questionnaire):
        return jsonify({'error': 'Permission denied'}), 403
    
    data = request.get_json()
    
    question.question_text = data.get('question_text', question.question_text)
    question.question_type = data.get('question_type', question.question_type)
    question.is_required = data.get('is_required', question.is_required)
    
    # Handle options for choice questions
    if data.get('options') and question.question_type in ['single_choice', 'multiple_choice']:
        options = [opt.strip() for opt in data.get('options', []) if opt.strip()]
        question.options = options
    else:
        question.options = []
    
    db.session.commit()
    
    current_app.logger.info(f'Question {question.id} updated by {current_user.username}')
    
    return jsonify({
        'success': True,
        'question': question.to_dict()
    })

@bp.route('/questions/<int:question_id>', methods=['DELETE'])
@login_required
def delete_question(question_id):
    """Delete question."""
    question = Question.query.get_or_404(question_id)
    questionnaire = question.questionnaire
    
    if not current_user.can_edit_questionnaire(questionnaire):
        return jsonify({'error': 'Permission denied'}), 403
    
    db.session.delete(question)
    db.session.commit()
    
    current_app.logger.info(f'Question {question.id} deleted by {current_user.username}')
    
    return jsonify({'success': True})

@bp.route('/questions/reorder', methods=['POST'])
@login_required
def reorder_questions():
    """Reorder questions."""
    data = request.get_json()
    questionnaire_id = data.get('questionnaire_id')
    question_ids = data.get('question_ids', [])
    
    questionnaire = Questionnaire.query.get_or_404(questionnaire_id)
    
    if not current_user.can_edit_questionnaire(questionnaire):
        return jsonify({'error': 'Permission denied'}), 403
    
    # Update order_index for each question
    for index, question_id in enumerate(question_ids):
        question = Question.query.get(question_id)
        if question and question.questionnaire_id == questionnaire.id:
            question.order_index = index
    
    db.session.commit()
    
    current_app.logger.info(f'Questions reordered for questionnaire {questionnaire.id} by {current_user.username}')
    
    return jsonify({'success': True})

@bp.route('/questionnaires/<int:questionnaire_id>/analytics', methods=['GET'])
@login_required
def get_analytics_data(questionnaire_id):
    """Get analytics data for charts."""
    questionnaire = Questionnaire.query.get_or_404(questionnaire_id)
    
    if not current_user.can_edit_questionnaire(questionnaire):
        return jsonify({'error': 'Permission denied'}), 403
    
    questions = questionnaire.get_questions()
    analytics_data = {}
    
    for question in questions:
        stats = question.get_answer_statistics()
        analytics_data[str(question.id)] = {
            'question_text': question.question_text,
            'question_type': question.question_type,
            'stats': stats
        }
    
    return jsonify({
        'questionnaire': questionnaire.to_dict(),
        'analytics': analytics_data
    })

@bp.route('/responses/<int:response_id>', methods=['GET'])
@login_required
def get_response(response_id):
    """Get detailed response data."""
    response = Response.query.get_or_404(response_id)
    questionnaire = response.questionnaire
    
    if not current_user.can_edit_questionnaire(questionnaire):
        return jsonify({'error': 'Permission denied'}), 403
    
    # Get all answers for this response
    answers_data = []
    for answer in response.answers:
        answers_data.append({
            'question_id': answer.question_id,
            'question_text': answer.question.question_text,
            'question_type': answer.question.question_type,
            'answer': answer.to_dict()
        })
    
    return jsonify({
        'response': response.to_dict(),
        'answers': answers_data
    })

@bp.route('/responses/<int:response_id>', methods=['DELETE'])
@login_required
def delete_response(response_id):
    """Delete a response."""
    response = Response.query.get_or_404(response_id)
    questionnaire = response.questionnaire
    
    if not current_user.can_edit_questionnaire(questionnaire):
        return jsonify({'error': 'Permission denied'}), 403
    
    db.session.delete(response)
    db.session.commit()
    
    current_app.logger.info(f'Response {response.id} deleted by {current_user.username}')
    
    return jsonify({'success': True})

@bp.route('/questionnaires/<int:questionnaire_id>/export', methods=['GET'])
@login_required
def export_responses(questionnaire_id):
    """Export responses as JSON."""
    questionnaire = Questionnaire.query.get_or_404(questionnaire_id)
    
    if not current_user.can_edit_questionnaire(questionnaire):
        return jsonify({'error': 'Permission denied'}), 403
    
    # Get all complete responses
    responses = Response.query.filter_by(
        questionnaire_id=questionnaire.id,
        is_complete=True
    ).all()
    
    export_data = {
        'questionnaire': questionnaire.to_dict(),
        'questions': [q.to_dict() for q in questionnaire.get_questions()],
        'responses': []
    }
    
    for response in responses:
        response_data = response.to_dict()
        response_data['answers'] = [a.to_dict() for a in response.answers]
        export_data['responses'].append(response_data)
    
    return jsonify(export_data)