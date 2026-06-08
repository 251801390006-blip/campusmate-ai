import re
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, BooleanField, TextAreaField
from wtforms.validators import DataRequired, Length, EqualTo, Regexp, ValidationError

# Flexible Regex Email Validation (Supports all standard, academic, and custom domain suffixes)
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

class LoginForm(FlaskForm):
    email = StringField('Email Address', validators=[
        DataRequired(message="Email is required."),
        Regexp(EMAIL_REGEX, message="Please enter a valid email address (e.g., user@university.edu.in).")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required.")
    ])
    remember_me = BooleanField('Remember Me')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(message="Username is required."),
        Length(min=3, max=30, message="Username must be between 3 and 30 characters."),
        Regexp(r'^[a-zA-Z0-9_]+$', message="Username must only contain letters, numbers, and underscores.")
    ])
    email = StringField('Email Address', validators=[
        DataRequired(message="Email is required."),
        Regexp(EMAIL_REGEX, message="Please enter a valid email address (e.g., student@nit.ac.in).")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required."),
        Length(min=8, message="Password must be at least 8 characters long.")
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message="Please confirm your password."),
        EqualTo('password', message="Passwords must match.")
    ])
    academic_level = SelectField('Academic Level', choices=[
        ('HIGH_SCHOOL', 'High School Student'),
        ('UNDERGRADUATE', 'Undergraduate Student'),
        ('POSTGRADUATE', 'Postgraduate / Master Student'),
        ('SELF_LEARNER', 'Self Learner')
    ], default='UNDERGRADUATE')

class FeedbackForm(FlaskForm):
    title = StringField('Feedback Title', validators=[
        DataRequired(message="Title is required."),
        Length(min=5, max=100, message="Title must be between 5 and 100 characters.")
    ])
    category = SelectField('Category', choices=[
        ('suggestion', 'Community Suggestion'),
        ('bug', 'Bug / Code Defect'),
        ('issue', 'General Issue'),
        ('feature_request', 'Feature Request')
    ], default='suggestion')
    content = TextAreaField('Description', validators=[
        DataRequired(message="Description is required."),
        Length(min=10, message="Description must be at least 10 characters long.")
    ])
    is_public = BooleanField('Share publicly with community suggestions', default=True)

class ReplyForm(FlaskForm):
    content = TextAreaField('Reply Message', validators=[
        DataRequired(message="Reply content is required."),
        Length(min=2, message="Reply must be at least 2 characters long.")
    ])
