from functools import wraps
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, abort, request
from flask_login import login_required, current_user
from models import db, Quiz, Question, Attempt, Response

student_bp = Blueprint('student', __name__, url_prefix='/student')


def student_required(f):
    @wraps(f)
    def dec(*a, **kw):
        if not current_user.is_authenticated or not current_user.is_student:
            flash('Access restricted to Students.', 'warning')
            abort(403)
        return f(*a, **kw)
    return dec


# ── Dashboard ──────────────────────────────────────────────────────────────────
@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    quizzes     = Quiz.query.filter_by(is_published=True)\
                            .order_by(Quiz.created_at.desc()).all()
    my_attempts = Attempt.query.filter_by(student_id=current_user.id, completed=True)\
                               .order_by(Attempt.completed_at.desc()).all()
    attempted_ids = {a.quiz_id for a in my_attempts}
    avg_score     = round(sum(a.score_percentage for a in my_attempts) / len(my_attempts), 1) \
                    if my_attempts else 0
    categories = sorted(set(q.category for q in quizzes))
    return render_template('student/dashboard.html',
                           quizzes=quizzes, my_attempts=my_attempts[:5],
                           attempted_ids=attempted_ids, avg_score=avg_score,
                           total_attempts=len(my_attempts), categories=categories,
                           title='Browse Quizzes')


# ── Quiz Detail ────────────────────────────────────────────────────────────────
@student_bp.route('/quiz/<int:quiz_id>')
@login_required
@student_required
def quiz_detail(quiz_id):
    quiz = Quiz.query.filter_by(id=quiz_id, is_published=True).first_or_404()
    prev = Attempt.query.filter_by(
        student_id=current_user.id, quiz_id=quiz_id, completed=True
    ).order_by(Attempt.completed_at.desc()).all()
    return render_template('student/quiz_detail.html',
                           quiz=quiz, prev_attempts=prev, title=quiz.title)


# ── Start Quiz ─────────────────────────────────────────────────────────────────
@student_bp.route('/quiz/<int:quiz_id>/start', methods=['POST'])
@login_required
@student_required
def start_quiz(quiz_id):
    quiz = Quiz.query.filter_by(id=quiz_id, is_published=True).first_or_404()
    if quiz.question_count == 0:
        flash('This quiz has no questions yet.', 'warning')
        return redirect(url_for('student.dashboard'))
    max_score = sum(q.marks for q in quiz.questions.all())
    attempt   = Attempt(student_id=current_user.id, quiz_id=quiz.id, max_score=max_score)
    db.session.add(attempt)
    db.session.commit()
    return redirect(url_for('student.attempt_quiz',
                            quiz_id=quiz.id, attempt_id=attempt.id, q=1))


# ── Attempt Quiz ───────────────────────────────────────────────────────────────
@student_bp.route('/quiz/<int:quiz_id>/attempt/<int:attempt_id>', methods=['GET', 'POST'])
@login_required
@student_required
def attempt_quiz(quiz_id, attempt_id):
    quiz    = Quiz.query.filter_by(id=quiz_id, is_published=True).first_or_404()
    attempt = Attempt.query.get_or_404(attempt_id)

    if attempt.student_id != current_user.id:
        abort(403)
    if attempt.completed:
        return redirect(url_for('student.result', attempt_id=attempt.id))

    questions = quiz.questions.order_by(Question.order_num).all()
    total_qs  = len(questions)
    q_num     = max(1, min(request.args.get('q', 1, type=int), total_qs))
    question  = questions[q_num - 1]
    existing  = Response.query.filter_by(
                    attempt_id=attempt.id, question_id=question.id
                ).first()

    if request.method == 'POST':
        # Only record response if not already answered
        if not existing:
            selected = request.form.get('answer')           # radio value A/B/C/D
            if selected not in ('A', 'B', 'C', 'D'):
                selected = None                              # skip / invalid = None

            is_correct    = (selected == question.correct_option) if selected else False
            marks_awarded = question.marks if is_correct else 0

            resp = Response(
                attempt_id      = attempt.id,
                question_id     = question.id,
                selected_option = selected,
                is_correct      = is_correct,
                marks_awarded   = marks_awarded
            )
            db.session.add(resp)
            db.session.commit()

        # After saving, decide where to go
        is_last = (q_num == total_qs)

        if is_last:
            # Last question done — go to submit/confirmation page
            return redirect(url_for('student.submit_quiz',
                                    quiz_id=quiz.id, attempt_id=attempt.id))
        else:
            # Go to next question
            return redirect(url_for('student.attempt_quiz',
                                    quiz_id=quiz.id, attempt_id=attempt.id,
                                    q=q_num + 1))

    # GET request — refresh answered set
    answered_ids = {r.question_id for r in attempt.responses.all()}

    return render_template('student/attempt.html',
                           quiz=quiz, attempt=attempt,
                           question=question, questions=questions,
                           q_num=q_num, existing=existing,
                           answered_ids=answered_ids,
                           progress=len(answered_ids),
                           title=f'Q{q_num} — {quiz.title}')


# ── Submit Confirmation ────────────────────────────────────────────────────────
@student_bp.route('/quiz/<int:quiz_id>/attempt/<int:attempt_id>/submit',
                  methods=['GET', 'POST'])
@login_required
@student_required
def submit_quiz(quiz_id, attempt_id):
    quiz    = Quiz.query.filter_by(id=quiz_id, is_published=True).first_or_404()
    attempt = Attempt.query.get_or_404(attempt_id)

    if attempt.student_id != current_user.id:
        abort(403)
    if attempt.completed:
        return redirect(url_for('student.result', attempt_id=attempt.id))

    questions    = quiz.questions.order_by(Question.order_num).all()
    answered_ids = {r.question_id for r in attempt.responses.all()}

    if request.method == 'POST':
        # Fill any unanswered questions with None responses
        for q in questions:
            if q.id not in answered_ids:
                db.session.add(Response(
                    attempt_id      = attempt.id,
                    question_id     = q.id,
                    selected_option = None,
                    is_correct      = False,
                    marks_awarded   = 0
                ))
        db.session.flush()

        attempt.total_score  = sum(r.marks_awarded for r in attempt.responses.all())
        attempt.completed    = True
        attempt.completed_at = datetime.utcnow()
        db.session.commit()

        flash('Quiz submitted! Here are your results.', 'success')
        return redirect(url_for('student.result', attempt_id=attempt.id))

    answered   = len(answered_ids)
    unanswered = len(questions) - answered
    return render_template('student/submit_confirm.html',
                           quiz=quiz, attempt=attempt,
                           answered=answered, unanswered=unanswered,
                           title='Submit Quiz')


# ── Result ─────────────────────────────────────────────────────────────────────
@student_bp.route('/result/<int:attempt_id>')
@login_required
@student_required
def result(attempt_id):
    attempt = Attempt.query.get_or_404(attempt_id)
    if attempt.student_id != current_user.id:
        abort(403)
    if not attempt.completed:
        return redirect(url_for('student.attempt_quiz',
                                quiz_id=attempt.quiz_id, attempt_id=attempt.id))

    quiz      = attempt.quiz
    questions = quiz.questions.order_by(Question.order_num).all()
    responses = {r.question_id: r for r in attempt.responses.all()}
    review    = [{'question': q, 'response': responses.get(q.id)} for q in questions]

    correct = sum(1 for r in responses.values() if r.is_correct)
    skipped = sum(1 for r in responses.values() if r.selected_option is None)

    return render_template('student/result.html',
                           attempt=attempt, quiz=quiz, review=review,
                           correct_count=correct, skipped_count=skipped,
                           total=len(questions), title='Result')


# ── History ────────────────────────────────────────────────────────────────────
@student_bp.route('/history')
@login_required
@student_required
def history():
    attempts = Attempt.query.filter_by(student_id=current_user.id, completed=True)\
                            .order_by(Attempt.completed_at.desc()).all()
    avg  = round(sum(a.score_percentage for a in attempts) / len(attempts), 1) if attempts else 0
    best = max((a.score_percentage for a in attempts), default=0)
    return render_template('student/history.html',
                           attempts=attempts, avg_score=avg, best_score=best,
                           title='My History')
