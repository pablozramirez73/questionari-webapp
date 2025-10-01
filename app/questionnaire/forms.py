"""
Questionnaire forms
"""
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, BooleanField, SubmitField, FieldList, FormField
from wtforms.validators import DataRequired, Length, Optional

class QuestionForm(FlaskForm):
    """Form for individual questions."""
    question_text = TextAreaField('Question Text', validators=[DataRequired(), Length(max=1000)])
    question_type = SelectField('Question Type', choices=[
        ('single_choice', 'Single Choice'),
        ('multiple_choice', 'Multiple Choice'),
        ('open_ended', 'Open Ended'),
        ('scale_1_5', 'Scale 1-5')
    ], validators=[DataRequired()])
    options = TextAreaField('Options (one per line, for choice questions)', validators=[Optional()])
    is_required = BooleanField('Required Question')

class QuestionnaireForm(FlaskForm):
    """Form for creating/editing questionnaires."""
    title = StringField('Title', validators=[DataRequired(), Length(min=5, max=200)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=1000)])
    is_public = BooleanField('Public (visible to all users)', default=True)
    allow_anonymous = BooleanField('Allow anonymous responses', default=False)
    allow_multiple_responses = BooleanField('Allow multiple responses from same user', default=False)
    submit = SubmitField('Save Questionnaire')

class ResponseForm(FlaskForm):
    """Base form for questionnaire responses."""
    submit = SubmitField('Submit Response')
    save_draft = SubmitField('Save as Draft')

class QuestionnaireSettingsForm(FlaskForm):
    """Form for questionnaire settings."""
    is_active = BooleanField('Active')
    is_public = BooleanField('Public')
    allow_anonymous = BooleanField('Allow Anonymous Responses')
    allow_multiple_responses = BooleanField('Allow Multiple Responses')
    submit = SubmitField('Update Settings')