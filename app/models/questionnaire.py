"""
Questionnaire and Question models
"""
import json
from datetime import datetime
from app import db

class Questionnaire(db.Model):
    """Questionnaire model."""
    
    __tablename__ = 'questionnaires'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_public = db.Column(db.Boolean, default=True, nullable=False)
    allow_anonymous = db.Column(db.Boolean, default=False, nullable=False)
    allow_multiple_responses = db.Column(db.Boolean, default=False, nullable=False)
    
    # Relationships
    questions = db.relationship('Question', backref='questionnaire', lazy='dynamic',
                              cascade='all, delete-orphan', order_by='Question.order_index')
    responses = db.relationship('Response', backref='questionnaire', lazy='dynamic',
                              cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Questionnaire {self.title}>'
    
    def get_questions(self):
        """Get questions ordered by index."""
        return self.questions.order_by(Question.order_index).all()
    
    def get_response_count(self):
        """Get total response count."""
        return self.responses.filter_by(is_complete=True).count()
    
    def get_completion_rate(self):
        """Calculate completion rate."""
        total_responses = self.responses.count()
        complete_responses = self.responses.filter_by(is_complete=True).count()
        if total_responses == 0:
            return 0
        return round((complete_responses / total_responses) * 100, 2)
    
    def user_has_responded(self, user_id):
        """Check if user has already responded."""
        if not user_id:
            return False
        return self.responses.filter_by(user_id=user_id, is_complete=True).first() is not None
    
    def can_user_respond(self, user):
        """Check if user can respond to questionnaire."""
        if not self.is_active:
            return False
        
        if not user and not self.allow_anonymous:
            return False
        
        if user and not self.allow_multiple_responses and self.user_has_responded(user.id):
            return False
        
        return True
    
    def get_statistics(self):
        """Get questionnaire statistics."""
        questions_count = self.questions.count()
        responses_count = self.get_response_count()
        completion_rate = self.get_completion_rate()
        
        return {
            'questions_count': questions_count,
            'responses_count': responses_count,
            'completion_rate': completion_rate,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_dict(self):
        """Convert questionnaire to dictionary."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'creator_id': self.creator_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'is_public': self.is_public,
            'allow_anonymous': self.allow_anonymous,
            'allow_multiple_responses': self.allow_multiple_responses,
            'questions_count': self.questions.count(),
            'responses_count': self.get_response_count()
        }

class Question(db.Model):
    """Question model."""
    
    __tablename__ = 'questions'
    
    QUESTION_TYPES = [
        ('single_choice', 'Single Choice'),
        ('multiple_choice', 'Multiple Choice'),
        ('open_ended', 'Open Ended'),
        ('scale_1_5', 'Scale 1-5')
    ]
    
    id = db.Column(db.Integer, primary_key=True)
    questionnaire_id = db.Column(db.Integer, db.ForeignKey('questionnaires.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), nullable=False)
    options_json = db.Column(db.Text)  # JSON string for choice options
    is_required = db.Column(db.Boolean, default=False, nullable=False)
    order_index = db.Column(db.Integer, default=0, nullable=False)
    
    # Relationships
    answers = db.relationship('Answer', backref='question', lazy='dynamic',
                            cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Question {self.question_text[:50]}...>'
    
    @property
    def options(self):
        """Get options as list."""
        if self.options_json:
            try:
                return json.loads(self.options_json)
            except (json.JSONDecodeError, TypeError):
                return []
        return []
    
    @options.setter
    def options(self, value):
        """Set options from list."""
        if value:
            self.options_json = json.dumps(value)
        else:
            self.options_json = None
    
    def get_answer_statistics(self):
        """Get statistics for this question's answers."""
        stats = {
            'total_answers': 0,
            'answer_distribution': {}
        }
        
        answers = self.answers.join(Response).filter(Response.is_complete == True).all()
        stats['total_answers'] = len(answers)
        
        if self.question_type in ['single_choice', 'multiple_choice']:
            # Count frequency of each option
            for answer in answers:
                if answer.answer_text:
                    # Handle multiple choice (comma-separated values)
                    values = [v.strip() for v in answer.answer_text.split(',')]
                    for value in values:
                        if value:
                            stats['answer_distribution'][value] = \
                                stats['answer_distribution'].get(value, 0) + 1
                                
        elif self.question_type == 'scale_1_5':
            # Count frequency of each scale value
            for answer in answers:
                if answer.answer_value is not None:
                    scale_value = str(int(answer.answer_value))
                    stats['answer_distribution'][scale_value] = \
                        stats['answer_distribution'].get(scale_value, 0) + 1
                        
        elif self.question_type == 'open_ended':
            # For open-ended, just provide sample responses (limited)
            sample_responses = [a.answer_text for a in answers[:10] if a.answer_text]
            stats['sample_responses'] = sample_responses
        
        return stats
    
    def to_dict(self):
        """Convert question to dictionary."""
        return {
            'id': self.id,
            'questionnaire_id': self.questionnaire_id,
            'question_text': self.question_text,
            'question_type': self.question_type,
            'options': self.options,
            'is_required': self.is_required,
            'order_index': self.order_index
        }