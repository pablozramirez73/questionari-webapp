"""
User model and authentication
"""
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager

class User(UserMixin, db.Model):
    """User model for authentication and authorization."""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user', nullable=False)  # admin, creator, user
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relationships
    questionnaires = db.relationship('Questionnaire', backref='creator', lazy='dynamic',
                                   foreign_keys='Questionnaire.creator_id')
    responses = db.relationship('Response', backref='user', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        """Set password hash."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash."""
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        """Check if user is admin."""
        return self.role == 'admin'
    
    def is_creator(self):
        """Check if user can create questionnaires."""
        return self.role in ['admin', 'creator']
    
    def can_access_questionnaire(self, questionnaire):
        """Check if user can access a questionnaire."""
        if self.is_admin():
            return True
        if questionnaire.creator_id == self.id:
            return True
        if questionnaire.is_public:
            return True
        return False
    
    def can_edit_questionnaire(self, questionnaire):
        """Check if user can edit a questionnaire."""
        if self.is_admin():
            return True
        return questionnaire.creator_id == self.id
    
    def get_questionnaire_stats(self):
        """Get user's questionnaire statistics."""
        created = self.questionnaires.count()
        responded = self.responses.count()
        return {
            'created': created,
            'responded': responded
        }
    
    def to_dict(self):
        """Convert user to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'is_active': self.is_active
        }

@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login."""
    return User.query.get(int(user_id))