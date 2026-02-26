from flask_wtf import FlaskForm, RecaptchaField
from wtforms import (StringField, PasswordField, SelectField, TextAreaField,
                     IntegerField, BooleanField, SubmitField)
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, NumberRange, Optional
from models import User

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(3, 64)])
    email    = StringField('Email',    validators=[DataRequired(), Email(), Length(max=120)])
    role     = SelectField('I want to', choices=[('student','Student — Take Quizzes'),('creator','Creator — Build Quizzes')], validators=[DataRequired()])
    password         = PasswordField('Password',         validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    recaptcha         = RecaptchaField()
    submit = SubmitField('Create Account')

    def validate_username(self, f):
        if User.query.filter_by(username=f.data).first():
            raise ValidationError('Username already taken.')
    def validate_email(self, f):
        if User.query.filter_by(email=f.data.lower()).first():
            raise ValidationError('Email already registered.')

class LoginForm(FlaskForm):
    email    = StringField('Email',    validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Keep me signed in')
    recaptcha = RecaptchaField()
    submit   = SubmitField('Sign In')

class QuizForm(FlaskForm):
    title       = StringField('Quiz Title',   validators=[DataRequired(), Length(5, 150)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=1000)])
    category    = SelectField('Category', choices=[
        ('General Knowledge','General Knowledge'),('Mathematics','Mathematics'),
        ('Science','Science'),('Technology','Technology'),('History','History'),
        ('Geography','Geography'),('Literature','Literature'),('Programming','Programming'),
        ('Physics','Physics'),('Chemistry','Chemistry'),('Biology','Biology'),
        ('Economics','Economics'),('Sports','Sports'),('Music','Music'),('Other','Other'),
    ])
    difficulty   = SelectField('Difficulty', choices=[('Easy','Easy'),('Medium','Medium'),('Hard','Hard')])
    time_limit   = IntegerField('Time Limit (minutes)', validators=[DataRequired(), NumberRange(1, 180)], default=30)
    is_published = BooleanField('Publish immediately')
    submit       = SubmitField('Save Quiz')

class QuestionForm(FlaskForm):
    text           = TextAreaField('Question Text', validators=[DataRequired(), Length(5, 2000)])
    option_a       = StringField('Option A', validators=[DataRequired(), Length(max=400)])
    option_b       = StringField('Option B', validators=[DataRequired(), Length(max=400)])
    option_c       = StringField('Option C (optional)', validators=[Optional(), Length(max=400)])
    option_d       = StringField('Option D (optional)', validators=[Optional(), Length(max=400)])
    correct_option = SelectField('Correct Answer', choices=[('A','A'),('B','B'),('C','C'),('D','D')])
    marks          = IntegerField('Marks', validators=[DataRequired(), NumberRange(1, 10)], default=1)
    explanation    = TextAreaField('Explanation (optional)', validators=[Optional(), Length(max=1000)])
    submit         = SubmitField('Save Question')

    def validate_correct_option(self, f):
        if f.data == 'C' and not self.option_c.data:
            raise ValidationError('Option C must have content.')
        if f.data == 'D' and not self.option_d.data:
            raise ValidationError('Option D must have content.')
