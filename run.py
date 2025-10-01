#!/usr/bin/env python3
"""
Flask Application Entry Point
"""
import os
from app import create_app, db
from app.models import User, Questionnaire, Question, Response, Answer
from flask_migrate import Migrate

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
migrate = Migrate(app, db)

@app.shell_context_processor
def make_shell_context():
    """Make database models available in flask shell."""
    return {
        'db': db,
        'User': User,
        'Questionnaire': Questionnaire,
        'Question': Question,
        'Response': Response,
        'Answer': Answer
    }

@app.cli.command()
def init_db():
    """Initialize the database."""
    db.create_all()
    print('Initialized the database.')

@app.cli.command()
def create_admin():
    """Create an admin user."""
    from getpass import getpass
    from app.models import User
    
    username = input('Admin username: ')
    email = input('Admin email: ')
    password = getpass('Admin password: ')
    
    if User.query.filter_by(username=username).first():
        print('User already exists!')
        return
    
    admin = User(
        username=username,
        email=email,
        role='admin'
    )
    admin.set_password(password)
    
    db.session.add(admin)
    db.session.commit()
    print(f'Admin user {username} created successfully!')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)