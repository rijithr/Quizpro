import json, urllib.request, urllib.error
from functools import wraps
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   abort, request, jsonify, current_app)
from flask_login import login_required, current_user
from models import db, Quiz, Question, Attempt, Response
from forms import QuizForm, QuestionForm

creator_bp = Blueprint('creator', __name__, url_prefix='/creator')


def creator_required(f):
    @wraps(f)
    def dec(*a, **kw):
        if not current_user.is_authenticated or not current_user.is_creator:
            flash('Access restricted to Quiz Creators.', 'warning')
            abort(403)
        return f(*a, **kw)
    return dec


# ── Dashboard ──────────────────────────────────────────────────────────────────
@creator_bp.route('/dashboard')
@login_required
@creator_required
def dashboard():
    quizzes         = Quiz.query.filter_by(creator_id=current_user.id)\
                                .order_by(Quiz.created_at.desc()).all()
    total_attempts  = sum(q.attempt_count  for q in quizzes)
    total_questions = sum(q.question_count for q in quizzes)
    published       = sum(1 for q in quizzes if q.is_published)
    return render_template('creator/dashboard.html',
                           quizzes=quizzes,
                           total_attempts=total_attempts,
                           total_questions=total_questions,
                           published_count=published,
                           title='Creator Dashboard')


# ── Create Quiz ────────────────────────────────────────────────────────────────
@creator_bp.route('/quiz/create', methods=['GET', 'POST'])
@login_required
@creator_required
def create_quiz():
    form = QuizForm()
    if form.validate_on_submit():
        q = Quiz(
            title        = form.title.data.strip(),
            description  = (form.description.data or '').strip(),
            category     = form.category.data,
            difficulty   = form.difficulty.data,
            time_limit   = form.time_limit.data,
            is_published = form.is_published.data,
            creator_id   = current_user.id
        )
        db.session.add(q)
        db.session.commit()
        flash(f'Quiz "{q.title}" created! Add questions below.', 'success')
        return redirect(url_for('creator.manage_questions', quiz_id=q.id))
    return render_template('creator/quiz_form.html', form=form,
                           title='Create Quiz', action='Create')


# ── Edit Quiz ──────────────────────────────────────────────────────────────────
@creator_bp.route('/quiz/<int:quiz_id>/edit', methods=['GET', 'POST'])
@login_required
@creator_required
def edit_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.creator_id != current_user.id:
        abort(403)
    form = QuizForm(obj=quiz)
    if form.validate_on_submit():
        quiz.title        = form.title.data.strip()
        quiz.description  = (form.description.data or '').strip()
        quiz.category     = form.category.data
        quiz.difficulty   = form.difficulty.data
        quiz.time_limit   = form.time_limit.data
        quiz.is_published = form.is_published.data
        db.session.commit()
        flash('Quiz updated successfully.', 'success')
        return redirect(url_for('creator.manage_questions', quiz_id=quiz.id))
    return render_template('creator/quiz_form.html', form=form, quiz=quiz,
                           title='Edit Quiz', action='Update')


# ── Delete Quiz ────────────────────────────────────────────────────────────────
@creator_bp.route('/quiz/<int:quiz_id>/delete', methods=['POST'])
@login_required
@creator_required
def delete_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.creator_id != current_user.id:
        abort(403)
    title = quiz.title
    db.session.delete(quiz)
    db.session.commit()
    flash(f'Quiz "{title}" deleted.', 'success')
    return redirect(url_for('creator.dashboard'))


# ── Toggle Publish ─────────────────────────────────────────────────────────────
@creator_bp.route('/quiz/<int:quiz_id>/toggle', methods=['POST'])
@login_required
@creator_required
def toggle_publish(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.creator_id != current_user.id:
        abort(403)
    if not quiz.is_published and quiz.question_count == 0:
        flash('Add at least one question before publishing.', 'warning')
        return redirect(url_for('creator.manage_questions', quiz_id=quiz.id))
    quiz.is_published = not quiz.is_published
    db.session.commit()
    flash(f'Quiz {"published" if quiz.is_published else "unpublished"}.', 'success')
    return redirect(url_for('creator.dashboard'))


# ── Manage Questions ───────────────────────────────────────────────────────────
@creator_bp.route('/quiz/<int:quiz_id>/questions')
@login_required
@creator_required
def manage_questions(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.creator_id != current_user.id:
        abort(403)
    questions   = quiz.questions.order_by(Question.order_num).all()
    has_api_key = bool(current_app.config.get('GROQ_API_KEY', '').strip())
    return render_template('creator/manage_questions.html',
                           quiz=quiz,
                           questions=questions,
                           has_api_key=has_api_key,
                           title=f'Questions — {quiz.title}')


# ── Add Question ───────────────────────────────────────────────────────────────
@creator_bp.route('/quiz/<int:quiz_id>/question/add', methods=['GET', 'POST'])
@login_required
@creator_required
def add_question(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.creator_id != current_user.id:
        abort(403)
    form = QuestionForm()
    if form.validate_on_submit():
        q = Question(
            quiz_id        = quiz.id,
            text           = form.text.data.strip(),
            option_a       = form.option_a.data.strip(),
            option_b       = form.option_b.data.strip(),
            option_c       = (form.option_c.data or '').strip() or None,
            option_d       = (form.option_d.data or '').strip() or None,
            correct_option = form.correct_option.data,
            marks          = form.marks.data,
            explanation    = (form.explanation.data or '').strip() or None,
            order_num      = quiz.questions.count() + 1,
            ai_generated   = False
        )
        db.session.add(q)
        db.session.commit()
        flash('Question added successfully.', 'success')
        if request.form.get('add_another'):
            return redirect(url_for('creator.add_question', quiz_id=quiz.id))
        return redirect(url_for('creator.manage_questions', quiz_id=quiz.id))
    return render_template('creator/question_form.html', form=form, quiz=quiz,
                           title='Add Question', action='Add')


# ── Edit Question ──────────────────────────────────────────────────────────────
@creator_bp.route('/question/<int:qid>/edit', methods=['GET', 'POST'])
@login_required
@creator_required
def edit_question(qid):
    question = Question.query.get_or_404(qid)
    quiz     = question.quiz
    if quiz.creator_id != current_user.id:
        abort(403)
    form = QuestionForm(obj=question)
    if form.validate_on_submit():
        question.text           = form.text.data.strip()
        question.option_a       = form.option_a.data.strip()
        question.option_b       = form.option_b.data.strip()
        question.option_c       = (form.option_c.data or '').strip() or None
        question.option_d       = (form.option_d.data or '').strip() or None
        question.correct_option = form.correct_option.data
        question.marks          = form.marks.data
        question.explanation    = (form.explanation.data or '').strip() or None
        db.session.commit()
        flash('Question updated.', 'success')
        return redirect(url_for('creator.manage_questions', quiz_id=quiz.id))
    return render_template('creator/question_form.html', form=form, quiz=quiz,
                           question=question, title='Edit Question', action='Update')


# ── Delete Question ────────────────────────────────────────────────────────────
@creator_bp.route('/question/<int:qid>/delete', methods=['POST'])
@login_required
@creator_required
def delete_question(qid):
    question = Question.query.get_or_404(qid)
    quiz     = question.quiz
    if quiz.creator_id != current_user.id:
        abort(403)
    db.session.delete(question)
    db.session.commit()
    flash('Question deleted.', 'success')
    return redirect(url_for('creator.manage_questions', quiz_id=quiz.id))


# ── AI Generate — Groq ─────────────────────────────────────────────────────────
@creator_bp.route('/quiz/<int:quiz_id>/ai-generate', methods=['POST'])
@login_required
@creator_required
def ai_generate(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.creator_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    api_key = current_app.config.get('GROQ_API_KEY', '').strip()
    if not api_key:
        return jsonify({'error': 'No Groq API key. Open config.py and set GROQ_API_KEY.'}), 400

    body       = request.get_json(force=True) or {}
    topic      = (body.get('topic') or quiz.category).strip()
    difficulty = body.get('difficulty') or quiz.difficulty
    count      = min(max(int(body.get('count', 5)), 1), 20)
    model      = current_app.config.get('GROQ_MODEL', 'llama-3.3-70b-versatile')

    prompt = (
        f'Generate exactly {count} multiple choice quiz questions '
        f'about "{topic}" at {difficulty} difficulty.\n\n'
        'Return ONLY a raw JSON array — no markdown, no extra text.\n'
        'Each object must have these exact keys:\n'
        '  "question"    : question text\n'
        '  "option_a"    : first option\n'
        '  "option_b"    : second option\n'
        '  "option_c"    : third option\n'
        '  "option_d"    : fourth option\n'
        '  "correct"     : exactly one of "A", "B", "C", "D"\n'
        '  "explanation" : 1-2 sentences explaining the correct answer\n'
        '  "marks"       : integer — 1 easy, 2 medium, 3 hard\n\n'
        'All options must be plausible. Do NOT add letter prefixes to options. '
        'Return ONLY the JSON array.'
    )

    payload = json.dumps({
        'model': model,
        'messages': [
            {
                'role': 'system',
                'content': 'You are a quiz question generator. Output ONLY valid JSON arrays. No markdown, no extra text.'
            },
            {
                'role': 'user',
                'content': prompt
            }
        ],
        'temperature': 0.7,
        'max_tokens': 4096,
        'stream': False
    }).encode('utf-8')

    try:
        # ── Key fix: add User-Agent + Accept to bypass Cloudflare 1010 ──────────
        req = urllib.request.Request(
            'https://api.groq.com/openai/v1/chat/completions',
            data=payload,
            headers={
                'Content-Type':  'application/json',
                'Authorization': f'Bearer {api_key}',
                'User-Agent':    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept':        'application/json',
                'Accept-Language': 'en-US,en;q=0.9',
                'Origin':        'https://console.groq.com',
                'Referer':       'https://console.groq.com/',
            },
            method='POST'
        )

        with urllib.request.urlopen(req, timeout=45) as resp:
            result = json.loads(resp.read().decode('utf-8'))

        raw = result['choices'][0]['message']['content'].strip()

        # Strip markdown fences if model added them
        if '```' in raw:
            for part in raw.split('```'):
                part = part.strip()
                if part.startswith('json'):
                    part = part[4:].strip()
                if part.startswith('['):
                    raw = part
                    break

        # Find JSON array boundaries
        start = raw.find('[')
        end   = raw.rfind(']')
        if start == -1 or end == -1:
            return jsonify({'error': 'AI did not return a valid JSON array. Try again.'}), 500
        raw = raw[start:end + 1]

        questions = json.loads(raw)

        validated = []
        for q in questions:
            required = ('question', 'option_a', 'option_b', 'option_c', 'option_d', 'correct')
            if not all(k in q for k in required):
                continue
            correct = str(q['correct']).strip().upper()
            if correct not in ('A', 'B', 'C', 'D'):
                continue
            validated.append({
                'question':    str(q['question']).strip(),
                'option_a':    str(q['option_a']).strip(),
                'option_b':    str(q['option_b']).strip(),
                'option_c':    str(q['option_c']).strip(),
                'option_d':    str(q['option_d']).strip(),
                'correct':     correct,
                'explanation': str(q.get('explanation', '')).strip(),
                'marks':       max(1, min(int(q.get('marks', 1)), 10))
            })

        if not validated:
            return jsonify({'error': 'No valid questions in AI response. Try again.'}), 500

        return jsonify({'questions': validated})

    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8', errors='replace')
        if e.code == 401:
            return jsonify({'error': 'Invalid Groq API key. Get a new one at console.groq.com'}), 500
        if e.code == 403:
            return jsonify({'error': f'Groq access denied (403). Your key may be invalid or expired. Detail: {err_body[:200]}'}), 500
        if e.code == 429:
            return jsonify({'error': 'Rate limit hit. Wait a few seconds and try again.'}), 500
        return jsonify({'error': f'Groq API error {e.code}: {err_body[:300]}'}), 500

    except json.JSONDecodeError as e:
        return jsonify({'error': f'Could not parse AI response. Try again. ({str(e)})'}), 500

    except Exception as e:
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500


# ── Save AI Questions ──────────────────────────────────────────────────────────
@creator_bp.route('/quiz/<int:quiz_id>/ai-save', methods=['POST'])
@login_required
@creator_required
def ai_save(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.creator_id != current_user.id:
        abort(403)

    data      = request.get_json(force=True) or {}
    questions = data.get('questions', [])
    saved     = 0

    for q in questions:
        if not q.get('selected', True):
            continue
        order = quiz.questions.count() + 1
        new_q = Question(
            quiz_id        = quiz.id,
            text           = q.get('question', '').strip(),
            option_a       = q.get('option_a', '').strip(),
            option_b       = q.get('option_b', '').strip(),
            option_c       = q.get('option_c', '').strip() or None,
            option_d       = q.get('option_d', '').strip() or None,
            correct_option = q.get('correct', 'A').upper(),
            marks          = int(q.get('marks', 1)),
            explanation    = q.get('explanation', '').strip() or None,
            order_num      = order,
            ai_generated   = True
        )
        db.session.add(new_q)
        saved += 1

    db.session.commit()
    return jsonify({'saved': saved, 'message': f'{saved} question(s) added to quiz!'})


# ── Analytics ──────────────────────────────────────────────────────────────────
@creator_bp.route('/quiz/<int:quiz_id>/analytics')
@login_required
@creator_required
def analytics(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.creator_id != current_user.id:
        abort(403)

    completed  = Attempt.query.filter_by(quiz_id=quiz.id, completed=True)\
                              .order_by(Attempt.completed_at.desc()).all()
    questions  = quiz.questions.order_by(Question.order_num).all()

    q_stats = []
    for q in questions:
        total   = Response.query.filter_by(question_id=q.id).count()
        correct = Response.query.filter_by(question_id=q.id, is_correct=True).count()
        q_stats.append({
            'question': q,
            'total':    total,
            'correct':  correct,
            'accuracy': round(correct / total * 100, 1) if total else 0
        })

    avg_score    = round(sum(a.score_percentage for a in completed) / len(completed), 1) if completed else 0
    best_score   = max((a.score_percentage       for a in completed), default=0)
    avg_duration = round(sum(a.duration_minutes  for a in completed) / len(completed), 1) if completed else 0

    return render_template('creator/analytics.html',
                           quiz=quiz, attempts=completed, q_stats=q_stats,
                           avg_score=avg_score, best_score=best_score,
                           avg_duration=avg_duration,
                           title=f'Analytics — {quiz.title}')
