from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(64),  unique=True, nullable=False, index=True)
    email         = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(20),  nullable=False, default='student')
    created_at    = db.Column(db.DateTime,    default=datetime.utcnow)

    quizzes  = db.relationship('Quiz',    backref='creator', lazy='dynamic', cascade='all, delete-orphan')
    attempts = db.relationship('Attempt', backref='student', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, pw):   self.password_hash = generate_password_hash(pw)
    def check_password(self, pw): return check_password_hash(self.password_hash, pw)
    @property
    def is_creator(self): return self.role == 'creator'
    @property
    def is_student(self): return self.role == 'student'

class Quiz(db.Model):
    __tablename__ = 'quizzes'
    id           = db.Column(db.Integer, primary_key=True)
    title        = db.Column(db.String(150), nullable=False)
    description  = db.Column(db.Text,        nullable=True)
    category     = db.Column(db.String(80),  nullable=False, default='General')
    difficulty   = db.Column(db.String(20),  nullable=False, default='Medium')
    time_limit   = db.Column(db.Integer,     nullable=False, default=30)
    is_published = db.Column(db.Boolean,     default=False)
    created_at   = db.Column(db.DateTime,    default=datetime.utcnow)
    updated_at   = db.Column(db.DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)
    creator_id   = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    questions = db.relationship('Question', backref='quiz', lazy='dynamic',
                                cascade='all, delete-orphan', order_by='Question.order_num')
    attempts  = db.relationship('Attempt',  backref='quiz', lazy='dynamic',
                                cascade='all, delete-orphan')

    @property
    def question_count(self): return self.questions.count()
    @property
    def attempt_count(self):  return self.attempts.count()
    @property
    def avg_score(self):
        atts = self.attempts.filter_by(completed=True).all()
        return round(sum(a.score_percentage for a in atts) / len(atts), 1) if atts else 0

class Question(db.Model):
    __tablename__ = 'questions'
    id             = db.Column(db.Integer, primary_key=True)
    quiz_id        = db.Column(db.Integer, db.ForeignKey('quizzes.id', ondelete='CASCADE'), nullable=False)
    text           = db.Column(db.Text,       nullable=False)
    option_a       = db.Column(db.String(400), nullable=False)
    option_b       = db.Column(db.String(400), nullable=False)
    option_c       = db.Column(db.String(400), nullable=True)
    option_d       = db.Column(db.String(400), nullable=True)
    correct_option = db.Column(db.String(1),   nullable=False)
    marks          = db.Column(db.Integer,     nullable=False, default=1)
    explanation    = db.Column(db.Text,        nullable=True)
    order_num      = db.Column(db.Integer,     nullable=False, default=0)
    ai_generated   = db.Column(db.Boolean,     default=False)

    responses = db.relationship('Response', backref='question', lazy='dynamic',
                                cascade='all, delete-orphan')

    @property
    def options(self):
        o = {'A': self.option_a, 'B': self.option_b}
        if self.option_c: o['C'] = self.option_c
        if self.option_d: o['D'] = self.option_d
        return o

class Attempt(db.Model):
    __tablename__ = 'attempts'
    id           = db.Column(db.Integer, primary_key=True)
    student_id   = db.Column(db.Integer, db.ForeignKey('users.id',   ondelete='CASCADE'), nullable=False)
    quiz_id      = db.Column(db.Integer, db.ForeignKey('quizzes.id', ondelete='CASCADE'), nullable=False)
    started_at   = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    completed    = db.Column(db.Boolean,  default=False)
    total_score  = db.Column(db.Integer,  default=0)
    max_score    = db.Column(db.Integer,  default=0)

    responses = db.relationship('Response', backref='attempt', lazy='dynamic',
                                cascade='all, delete-orphan')

    @property
    def score_percentage(self):
        return round((self.total_score / self.max_score) * 100, 1) if self.max_score else 0
    @property
    def grade(self):
        p = self.score_percentage
        if p >= 90: return ('A+', 'Exceptional')
        if p >= 80: return ('A',  'Excellent')
        if p >= 70: return ('B',  'Good')
        if p >= 60: return ('C',  'Average')
        if p >= 50: return ('D',  'Below Average')
        return ('F', 'Needs Improvement')
    @property
    def duration_minutes(self):
        if self.completed_at and self.started_at:
            return round((self.completed_at - self.started_at).total_seconds() / 60, 1)
        return 0

class Response(db.Model):
    __tablename__ = 'responses'
    id              = db.Column(db.Integer, primary_key=True)
    attempt_id      = db.Column(db.Integer, db.ForeignKey('attempts.id',  ondelete='CASCADE'), nullable=False)
    question_id     = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False)
    selected_option = db.Column(db.String(1), nullable=True)
    is_correct      = db.Column(db.Boolean,   default=False)
    marks_awarded   = db.Column(db.Integer,   default=0)
