from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User
from forms import RegistrationForm, LoginForm

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET','POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('auth.dash'))
    form = RegistrationForm()
    if form.validate_on_submit():
        u = User(username=form.username.data.strip(),
                 email=form.email.data.lower().strip(),
                 role=form.role.data)
        u.set_password(form.password.data)
        db.session.add(u); db.session.commit()
        login_user(u)
        flash(f'Welcome, {u.username}! Account created.', 'success')
        return redirect(url_for('auth.dash'))
    return render_template('auth/register.html', form=form, title='Register')

@auth_bp.route('/login', methods=['GET','POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.dash'))
    form = LoginForm()
    if form.validate_on_submit():
        u = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if u and u.check_password(form.password.data):
            login_user(u, remember=form.remember.data)
            flash(f'Welcome back, {u.username}!', 'success')
            nxt = request.args.get('next')
            return redirect(nxt or url_for('auth.dash'))
        flash('Invalid email or password.', 'danger')
    return render_template('auth/login.html', form=form, title='Sign In')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Signed out successfully.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/dashboard')
@login_required
def dash():
    if current_user.role == 'admin':
        return redirect('/admin')
    if current_user.is_creator:
        return redirect(url_for('creator.dashboard'))
    return redirect(url_for('student.dashboard'))
