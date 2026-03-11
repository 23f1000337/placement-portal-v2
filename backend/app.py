"""
==========================================================
 Placement Portal - Main Application (backend/app.py)
==========================================================
 Entry point for the Flask application.
 Run from project root:  python backend/app.py
==========================================================
"""

import os
import sys
from dotenv import load_dotenv

# Ensure the project root is on sys.path so 'backend' package is importable
# even when running this file directly:  python backend/app.py
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Load environment variables from .env file at project root
load_dotenv(os.path.join(_project_root, '.env'))

from flask import Flask, send_from_directory
from flask_security import Security, SQLAlchemyUserDatastore, hash_password
from backend import config
from backend.extensions import db, cache, celery, mail
from backend.models import User, Role, Student, Company, PlacementDrive, Application, Placement


# ------------------------------------------------------------------
#  App Factory — creates and configures the Flask application
# ------------------------------------------------------------------

def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(config.BASE_DIR, 'frontend', 'templates'),
        static_folder=os.path.join(config.BASE_DIR, 'frontend', 'static')
    )

    # --- Basic config ---
    app.secret_key = config.SECRET_KEY
    app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
    app.config['CACHE_DEFAULT_TIMEOUT'] = config.CACHE_DEFAULT_TIMEOUT

    # --- Email (SMTP) config ---
    app.config['MAIL_SERVER'] = config.MAIL_SERVER
    app.config['MAIL_PORT'] = config.MAIL_PORT
    app.config['MAIL_USE_TLS'] = config.MAIL_USE_TLS
    app.config['MAIL_USERNAME'] = config.MAIL_USERNAME
    app.config['MAIL_PASSWORD'] = config.MAIL_PASSWORD
    app.config['MAIL_DEFAULT_SENDER'] = config.MAIL_DEFAULT_SENDER

    # --- Flask-Security config ---
    app.config['SECURITY_PASSWORD_SALT'] = config.SECURITY_PASSWORD_SALT
    app.config['SECURITY_REGISTERABLE'] = config.SECURITY_REGISTERABLE
    app.config['SECURITY_SEND_REGISTER_EMAIL'] = config.SECURITY_SEND_REGISTER_EMAIL
    app.config['WTF_CSRF_ENABLED'] = config.WTF_CSRF_ENABLED

    # --- Cache config — try Redis first, fallback to in-memory ---
    try:
        import redis as _redis
        _r = _redis.Redis.from_url(config.CACHE_REDIS_URL, socket_connect_timeout=5)
        _r.ping()
        app.config['CACHE_TYPE'] = 'RedisCache'
        app.config['CACHE_REDIS_URL'] = config.CACHE_REDIS_URL
    except Exception as _redis_err:
        print(f'[INFO] Redis not available — using SimpleCache instead ({_redis_err})')
        app.config['CACHE_TYPE'] = 'SimpleCache'

    # --- Initialize Flask extensions ---
    db.init_app(app)
    cache.init_app(app)
    mail.init_app(app)

    # --- Flask-Security setup ---
    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    security = Security(app, user_datastore, register_blueprint=False)
    app.login_manager.login_view = 'auth.login'
    app.user_datastore = user_datastore

    # Override Flask-Security's unauthenticated handler to redirect to our login
    @app.login_manager.unauthorized_handler
    def unauthn_handler():
        from flask import redirect, url_for
        return redirect(url_for('auth.login'))

    # Give Celery tasks access to Flask app context
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    celery.Task = ContextTask

    # --- Serve frontend JS/CSS component files ---
    @app.route('/frontend/<path:filename>')
    def serve_frontend(filename):
        return send_from_directory(
            os.path.join(config.BASE_DIR, 'frontend'), filename
        )

    # --- Register all Blueprints (routes) ---
    from backend.routes.auth import auth_bp
    from backend.routes.admin import admin_bp
    from backend.routes.company import company_bp
    from backend.routes.student import student_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(company_bp)
    app.register_blueprint(student_bp)

    # --- Create database tables + seed initial data ---
    with app.app_context():
        os.makedirs(os.path.join(config.BASE_DIR, 'instance'), exist_ok=True)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        db.create_all()

        # Create Flask-Security roles if they don't exist
        if not Role.query.first():
            for rname, rdesc in [('admin', 'Administrator'), ('student', 'Student'), ('company', 'Company')]:
                db.session.add(Role(name=rname, description=rdesc))
            db.session.commit()

        # Create default admin account if it doesn't exist
        if not User.query.filter_by(role='admin').first():
            admin = User(
                email='admin@placement.com',
                password=hash_password('admin123'),
                role='admin'
            )
            admin.roles.append(Role.query.filter_by(name='admin').first())
            db.session.add(admin)
            db.session.commit()
            print('[SEED] Admin created -> admin@placement.com / admin123')

        # Seed test data if database is empty
        if Student.query.count() == 0:
            _seed_test_data()
            print('[SEED] Test data added!')

    # Import celery tasks so they get registered
    import backend.tasks  # noqa: F401

    return app


# ------------------------------------------------------------------
#  Seed test data — students, companies, drives, applications
# ------------------------------------------------------------------

def _seed_test_data():
    from datetime import date, datetime, timedelta
    pwd = hash_password('test123')
    student_role = Role.query.filter_by(name='student').first()
    company_role = Role.query.filter_by(name='company').first()

    # --- 5 Test Students (password: test123) ---
    students_info = [
        ('Aarav Sharma',  'aarav@student.com',  'STU2001', 'CSE', 4, 8.7, '9876543210', 'Python, Java, ML'),
        ('Diya Patel',    'diya@student.com',   'STU2002', 'ECE', 4, 9.1, '9876543211', 'C++, Embedded, VLSI'),
        ('Rohan Gupta',   'rohan@student.com',  'STU2003', 'CSE', 3, 7.5, '9876543212', 'JavaScript, React, Node'),
        ('Priya Singh',   'priya@student.com',  'STU2004', 'ME',  4, 8.2, '9876543213', 'AutoCAD, SolidWorks, Python'),
        ('Vikram Reddy',  'vikram@student.com', 'STU2005', 'CSE', 4, 6.8, '9876543214', 'Java, Spring Boot, SQL'),
    ]
    students = []
    for name, email, roll, branch, year, cgpa, phone, skills in students_info:
        user = User(email=email, password=pwd, role='student')
        user.roles.append(student_role)
        db.session.add(user)
        db.session.flush()
        student = Student(
            user_id=user.id, name=name, roll_no=roll, branch=branch,
            year=year, cgpa=cgpa, phone=phone, skills=skills,
            about=f'{name} — {branch} student, Year {year}'
        )
        db.session.add(student)
        students.append(student)

    # --- 3 Test Companies (password: test123, pre-approved) ---
    companies_info = [
        ('TechNova Solutions',  'technova@company.com',   'IT Services',        'Neha Kapoor',
         'hr@technova.com',     '9988776601', 'https://technova.example.com',
         'Leading IT services company specialising in cloud and AI solutions.'),
        ('GreenField Motors',   'greenfield@company.com', 'Automobile',         'Rajesh Iyer',
         'hr@greenfield.com',   '9988776602', 'https://greenfield.example.com',
         'Electric vehicle manufacturer with global operations.'),
        ('FinEdge Analytics',   'finedge@company.com',    'Finance / Analytics', 'Sonal Mehta',
         'hr@finedge.com',      '9988776603', 'https://finedge.example.com',
         'Fintech company providing data-driven analytics for banking sector.'),
    ]
    companies = []
    for name, email, industry, hr_name, hr_email, hr_phone, website, desc in companies_info:
        user = User(email=email, password=pwd, role='company')
        user.roles.append(company_role)
        db.session.add(user)
        db.session.flush()
        company = Company(
            user_id=user.id, name=name, industry=industry,
            hr_name=hr_name, hr_email=hr_email, hr_phone=hr_phone,
            website=website, description=desc, status='approved'
        )
        db.session.add(company)
        companies.append(company)
    db.session.flush()

    # --- 6 Placement Drives (all approved, varied eligibility) ---
    today = date.today()
    drives_info = [
        (companies[0], 'Software Engineer',          'Full-time SDE role working on cloud microservices.',
         'CSE, ECE', 7.0, 4, 'Python, Java, Docker',         '12 LPA',    'Bangalore', today + timedelta(days=15)),
        (companies[0], 'Data Science Intern',        '6-month internship in the ML/AI team.',
         'CSE',      7.5, 3, 'Python, ML, Pandas',           '40K/month', 'Remote',    today + timedelta(days=10)),
        (companies[1], 'Mechanical Design Engineer', 'Design EV drivetrain components.',
         'ME',       7.0, 4, 'AutoCAD, SolidWorks',          '10 LPA',    'Pune',      today + timedelta(days=20)),
        (companies[1], 'Embedded Systems Engineer',  'Firmware for EV battery management.',
         'ECE, CSE', 7.5, 4, 'C, Embedded C, RTOS',          '11 LPA',    'Chennai',   today + timedelta(days=25)),
        (companies[2], 'Data Analyst',               'Analyse banking transaction data for fraud detection.',
         'CSE, ECE, ME', 6.5, 4, 'SQL, Python, Tableau',     '9 LPA',     'Mumbai',    today + timedelta(days=12)),
        (companies[2], 'Backend Developer',          'Build REST APIs for fintech platform.',
         'CSE',      8.0, 4, 'Java, Spring Boot, PostgreSQL', '14 LPA',    'Hyderabad', today + timedelta(days=30)),
    ]
    drives = []
    for comp, title, desc, branches, min_cgpa, year, skills, salary, loc, deadline in drives_info:
        drive = PlacementDrive(
            company_id=comp.id, title=title, description=desc,
            eligible_branches=branches, min_cgpa=min_cgpa,
            eligible_year=year, skills_required=skills,
            salary=salary, location=loc, deadline=deadline,
            status='approved'
        )
        db.session.add(drive)
        drives.append(drive)
    db.session.flush()

    # --- 8 Sample Applications ---
    applications = [
        # Aarav (CSE, 8.7) → Software Engineer (shortlisted) + Data Analyst (applied)
        (students[0], drives[0], 'shortlisted', today + timedelta(days=8)),
        (students[0], drives[4], 'applied',     None),
        # Diya (ECE, 9.1) → Software Engineer (applied) + Embedded Systems (shortlisted)
        (students[1], drives[0], 'applied',     None),
        (students[1], drives[3], 'shortlisted', today + timedelta(days=12)),
        # Rohan (CSE, 7.5) → Data Science Intern (selected)
        (students[2], drives[1], 'selected',    today + timedelta(days=5)),
        # Priya (ME, 8.2) → Mech Design (applied) + Data Analyst (rejected)
        (students[3], drives[2], 'applied',     None),
        (students[3], drives[4], 'rejected',    None),
        # Vikram (CSE, 6.8) → Data Analyst (applied)
        (students[4], drives[4], 'applied',     None),
    ]
    for stu, drive, status, interview_dt in applications:
        app_record = Application(
            student_id=stu.id, drive_id=drive.id, status=status,
            interview_date=datetime.combine(interview_dt, datetime.min.time()) if interview_dt else None
        )
        db.session.add(app_record)

    db.session.commit()


# ------------------------------------------------------------------
#  Run the app directly: python backend/app.py
# ------------------------------------------------------------------

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
