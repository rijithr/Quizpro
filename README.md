# QuizPro — AI-Powered Quiz Platform
**Flask · SQLAlchemy · Flask-Login · Flask-WTF · Claude AI**

---

## Quick Start

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) Set your Anthropic API key for AI generation
export ANTHROPIC_API_KEY=sk-ant-your-key-here

# 4. Run
python app.py

# 5. Open http://127.0.0.1:5000
```

The SQLite database (`quizpro.db`) is auto-created on first run.

---

## Features

### Authentication
- Register as **Student** or **Quiz Creator**
- Secure password hashing (Werkzeug)
- Session management (Flask-Login)
- CSRF protection on all forms (Flask-WTF)
- Google reCAPTCHA v2 on login/register pages (set `RECAPTCHA_PUBLIC_KEY`/`RECAPTCHA_PRIVATE_KEY` in `config.py` or via environment variables)
- Role-based access control (`@creator_required`, `@student_required`)

### Quiz Creator
- Full CRUD: create, edit, delete quizzes
- Full CRUD: add, edit, delete questions
- **AI Question Generator**: select topic, difficulty, count → Claude generates questions with options, correct answers, and explanations
- Preview and selectively save AI-generated questions
- Publish/unpublish control
- Analytics: per-question accuracy, attempt log, avg/best score

### Student
- Browse and filter quizzes (search, category, difficulty)
- Live countdown timer (auto-submits on timeout)
- One-question-at-a-time interface
- Skip questions, review before submitting
- Detailed results: score ring, grade (A+→F), per-question review with explanations
- Full attempt history

---

## AI Question Generation

Requires `ANTHROPIC_API_KEY` environment variable.

On the **Manage Questions** page, use the AI panel:
1. Enter topic/subject
2. Select difficulty and count
3. Click **Generate Questions with AI**
4. Review the preview — select/deselect individual questions
5. Click **Save Selected Questions**

Questions are marked with a 🤖 badge.

---

## Project Structure

```
quizpro/
├── app.py              # Flask app factory
├── config.py           # Config (secret key, DB, API key)
├── models.py           # SQLAlchemy models
├── forms.py            # Flask-WTF forms
├── requirements.txt
├── routes/
│   ├── auth.py         # Register, login, logout
│   ├── creator.py      # Quiz CRUD + AI generation
│   └── student.py      # Browse, attempt, results
├── templates/
│   ├── base.html
│   ├── auth/           # login, register
│   ├── creator/        # dashboard, quiz_form, manage_questions, question_form, analytics
│   ├── student/        # dashboard, quiz_detail, attempt, submit_confirm, result, history
│   └── errors/         # 403, 404, 500
└── static/css/style.css
```

---

## Database Schema

```
users     → id, username, email, password_hash, role, created_at
quizzes   → id, title, description, category, difficulty, time_limit, is_published, creator_id
questions → id, quiz_id, text, option_a/b/c/d, correct_option, marks, explanation, order_num, ai_generated
attempts  → id, student_id, quiz_id, started_at, completed_at, completed, total_score, max_score
responses → id, attempt_id, question_id, selected_option, is_correct, marks_awarded
```

## Grading Scale

| % | Grade | Label |
|---|-------|-------|
| ≥90 | A+ | Exceptional |
| ≥80 | A  | Excellent |
| ≥70 | B  | Good |
| ≥60 | C  | Average |
| ≥50 | D  | Below Average |
| <50 | F  | Needs Improvement |
