from flask import Flask, redirect, url_for, render_template
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect
from config import Config
from models import db, User, Quiz, Question, Attempt, Response
from routes.auth    import auth_bp
from routes.creator import creator_bp
from routes.student import student_bp

from flask_admin import Admin, AdminIndexView, expose
from flask_admin.menu import MenuLink
from flask_admin.contrib.sqla import ModelView
from flask_wtf import FlaskForm
from flask import request

class MyAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if not (current_user.is_authenticated and current_user.role == 'admin'):
            return redirect(url_for('auth.login', next=request.url))
        return self.render('admin/index.html')

    @expose('/logout')
    def logout(self):
        return redirect(url_for('auth.logout'))

class AdminModelView(ModelView):
    form_base_class = FlaskForm
    def is_accessible(self):
        # Allow access if user is logged in and role is 'admin'
        return current_user.is_authenticated and current_user.role == 'admin'

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('auth.login', next=request.url))

class QuizModelView(AdminModelView):
    # This renders Questions directly underneath their respective Quiz detail page!
    inline_models = (Question,)
    column_list = ('title', 'creator', 'category', 'difficulty', 'is_published')
    column_searchable_list = ['title', 'category']
    column_filters = ['category', 'difficulty', 'is_published']

class QuestionModelView(AdminModelView):
    column_list = ('quiz', 'text', 'correct_option', 'marks', 'order_num')
    column_filters = ['quiz.title', 'correct_option']
    column_searchable_list = ['text', 'quiz.title']
    column_default_sort = ('quiz_id', False) # Auto-groups identical quizzes together visually

csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    csrf.init_app(app)          # ← makes csrf_token() available in ALL templates

    lm = LoginManager(app)
    lm.login_view              = 'auth.login'
    lm.login_message           = 'Please sign in to continue.'
    lm.login_message_category  = 'info'

    @lm.user_loader
    def load_user(uid): return User.query.get(int(uid))

    app.register_blueprint(auth_bp)
    app.register_blueprint(creator_bp)
    app.register_blueprint(student_bp)

    @app.errorhandler(403)
    def e403(e): return render_template('errors/403.html'), 403
    @app.errorhandler(404)
    def e404(e): return render_template('errors/404.html'), 404
    @app.errorhandler(500)
    def e500(e): return render_template('errors/500.html'), 500

    admin = Admin(app, name='QuizPro Admin', url='/admin', index_view=MyAdminIndexView())
    admin.add_view(AdminModelView(User, db.session))
    admin.add_view(QuizModelView(Quiz, db.session))
    admin.add_view(QuestionModelView(Question, db.session))
    admin.add_view(AdminModelView(Attempt, db.session))
    admin.add_view(AdminModelView(Response, db.session))
    admin.add_link(MenuLink(name='Logout', category='', url='/logout'))

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('auth.dash'))
        return redirect(url_for('auth.login'))

    with app.app_context():
        db.create_all()
        # Seed the admin user if it doesn't exist
        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin', email='admin@gmail.com', role='admin')
            admin_user.set_password('adminpass')
            db.session.add(admin_user)
            db.session.commit()

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
