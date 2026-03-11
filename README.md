
# Placement Portal V2

A full-stack campus placement management system built with Flask, Vue.js 3, Celery, and Redis.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask 3.1.3, Flask-Security-Too 5.7.1, Flask-SQLAlchemy |
| Frontend | Vue.js 3 (CDN), Bootstrap 5.3 |
| Database | SQLite |
| Caching | Redis (Flask-Caching) |
| Background Jobs | Celery 5.3.6 with Redis broker |
| Email | Flask-Mail (SMTP) |

## Project Structure

```
mad_2_project/
├── backend/
│   ├── app.py              # Flask app factory + entry point
│   ├── config.py           # Configuration settings
│   ├── extensions.py       # Flask extensions (db, cache, celery, mail)
│   ├── celery_worker.py    # Celery worker entry point
│   ├── tasks.py            # Celery tasks (reminders, reports, exports)
│   ├── helpers.py          # Utility functions
│   ├── models/
│   │   └── __init__.py     # SQLAlchemy models (User, Student, Company, etc.)
│   └── routes/
│       ├── auth.py         # Authentication routes
│       ├── admin.py        # Admin API & pages
│       ├── student.py      # Student API & pages
│       └── company.py      # Company API & pages
# Placement Portal V2

A campus placement management system built with Flask, Vue.js, Celery, and Redis.

This repository contains only the initial setup files for the project milestone.
# source .venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
pip install argon2-cffi requests
```

### 2. Configure Environment

Create a `.env` file in the project root (optional, for SMTP):

```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com
```

### 3. Run the Application

**Terminal 1 — Flask server:**
```bash
.venv\Scripts\activate
python backend/app.py
```

**Terminal 2 — Celery worker:**
```bash
.venv\Scripts\activate
celery -A backend.celery_worker.celery worker --loglevel=info --pool=solo
```

**Terminal 3 — Celery Beat (scheduled tasks):**
```bash
.venv\Scripts\activate
celery -A backend.celery_worker.celery beat --loglevel=info
```

The app runs at **http://127.0.0.1:5000**

## Default Accounts

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@placement.com | admin123 |
| Student | aarav@student.com | test123 |
| Student | diya@student.com | test123 |
| Company | technova@company.com | test123 |
| Company | greenfield@company.com | test123 |

Seed data (5 students, 3 companies, 6 drives, 8 applications) is created automatically on first run.
>>>>>>> d59e6df (Milestone-0 PPA-V2 Setup)
