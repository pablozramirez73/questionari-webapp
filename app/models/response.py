"""
Response and Answer models
"""
from datetime import datetime
from app import db

class Response(db.Model):
    """Response model for questionnaire submissions."""
    
    __tablename__ = 'responses'
    
    id = db.Column(db.Integer, primary_key=True)
    questionnaire_id = db.Column(db.Integer, db.ForeignKey('questionnaires.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Nullable for anonymous
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_complete = db.Column(db.Boolean, default=False, nullable=False)
    ip_address = db.Column(db.String(45))  # Store IP for anonymous responses
    user_agent = db.Column(db.String(500))  # Store user agent for tracking
    
    # Relationships
    answers = db.relationship('Answer', backref='response', lazy='dynamic',
                            cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Response {self.id} for Questionnaire {self.questionnaire_id}>'
    
    def get_completion_percentage(self):
        """Calculate completion percentage based on required questions."""
        questionnaire = self.questionnaire
        required_questions = questionnaire.questions.filter_by(is_required=True).count()
        
        if required_questions == 0:
            return 100 if self.answers.count() > 0 else 0
        
        answered_required = 0
        for question in questionnaire.questions.filter_by(is_required=True):
            if self.answers.filter_by(question_id=question.id).first():
                answered_required += 1
        
        return round((answered_required / required_questions) * 100, 2)
    
    def is_question_answered(self, question_id):
        """Check if a specific question is answered."""
        answer = self.answers.filter_by(question_id=question_id).first()
        if not answer:
            return False
        return bool(answer.answer_text or answer.answer_value is not None)
    
    def get_answer_for_question(self, question_id):
        """Get answer for a specific question."""
        return self.answers.filter_by(question_id=question_id).first()
    
    def can_be_edited(self):
        """Check if response can still be edited."""
        # Response can be edited if it's not complete or within edit window
        if not self.is_complete:
            return True
        
        # Add time-based editing window if needed (e.g., 24 hours)
        # edit_window = timedelta(hours=24)
        # return datetime.utcnow() - self.submitted_at < edit_window
        
        return False
    
    def get_respondent_info(self):
        """Get respondent information (respecting anonymity)."""
        if self.user:
            return {
                'type': 'registered',
                'username': self.user.username,
                'email': self.user.email,
                'id': self.user_id
            }
        else:
            return {
                'type': 'anonymous',
                'ip_address': self.ip_address,
                'user_agent': self.user_agent[:100] + '...' if len(self.user_agent or '') > 100 else self.user_agent
            }
    
    def to_dict(self):
        """Convert response to dictionary."""
        return {
            'id': self.id,
            'questionnaire_id': self.questionnaire_id,
            'user_id': self.user_id,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_complete': self.is_complete,
            'completion_percentage': self.get_completion_percentage(),
            'respondent_info': self.get_respondent_info()
        }

class Answer(db.Model):
    """Answer model for individual question responses."""
    
    __tablename__ = 'answers'
    
    id = db.Column(db.Integer, primary_key=True)
    response_id = db.Column(db.Integer, db.ForeignKey('responses.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    answer_text = db.Column(db.Text)  # For text-based answers
    answer_value = db.Column(db.Float)  # For numeric answers (scales, etc.)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Answer {self.id} for Question {self.question_id}>'
    
    def get_display_value(self):
        """Get formatted display value based on question type."""
        if self.question.question_type == 'scale_1_5':
            return f"{int(self.answer_value)}/5" if self.answer_value is not None else "No answer"
        elif self.question.question_type in ['single_choice', 'multiple_choice']:
            return self.answer_text or "No answer"
        elif self.question.question_type == 'open_ended':
            return self.answer_text or "No answer"
        else:
            return self.answer_text or str(self.answer_value) if self.answer_value is not None else "No answer"
    
    def set_value(self, value, question_type):
        """Set answer value based on question type."""
        if question_type == 'scale_1_5':
            try:
                self.answer_value = float(value)
                self.answer_text = None
            except (ValueError, TypeError):
                self.answer_value = None
                self.answer_text = None
        elif question_type in ['single_choice', 'multiple_choice', 'open_ended']:
            self.answer_text = str(value) if value is not None else None
            self.answer_value = None
        else:
            # Default to text
            self.answer_text = str(value) if value is not None else None
            self.answer_value = None
    
    def to_dict(self):
        """Convert answer to dictionary."""
        return {
            'id': self.id,
            'response_id': self.response_id,
            'question_id': self.question_id,
            'answer_text': self.answer_text,
            'answer_value': self.answer_value,
            'display_value': self.get_display_value(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }