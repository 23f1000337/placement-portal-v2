"""
Authentication routes — login, logout, registration, file serving.
"""

import os
from flask import Blueprint, render_template, redirect, url_for, request, flash, \
    send_from_directory, current_app
from flask_login import login_user, logout_user
from flask_security import login_required, current_user, hash_password, verify_and_update_password
from werkzeug.utils import secure_filename

from backend.extensions import db
from backend.models import User, Student, Company, Role
from backend.helpers import allowed_file

auth_bp = Blueprint('auth', __name__)


# ------------------------------------------------------------------
#  Home page — redirects logged-in users to their dashboard
# ------------------------------------------------------------------

@auth_bp.route('/')
def home():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.admin_dashboard'))
        elif current_user.role == 'company':
            return redirect(url_for('company.company_dashboard'))
        else:
            return redirect(url_for('student.student_dashboard'))
    return render_template('index.html')


# ------------------------------------------------------------------
#  Login
# ------------------------------------------------------------------

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.home'))

    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password']
        role = request.form['role']

        user = User.query.filter_by(email=email).first()

        if not user or not verify_and_update_password(password, user):
            flash('Invalid email or password.', 'danger')
            return redirect(url_for('auth.login'))

        if user.role != role:
            flash('Incorrect role selected for this account.', 'danger')
            return redirect(url_for('auth.login'))

        if user.is_blacklisted:
            flash('Your account has been blacklisted. Contact admin.', 'danger')
            return redirect(url_for('auth.login'))

        login_user(user)
        flash('Logged in!', 'success')

        # Redirect based on role
        if user.role == 'admin':
            return redirect(url_for('admin.admin_dashboard'))
        elif user.role == 'company':
            if user.company.status != 'approved':
                return redirect(url_for('company.company_pending'))
            return redirect(url_for('company.company_dashboard'))
        else:
            return redirect(url_for('student.student_dashboard'))

    return render_template('login.html')


# ------------------------------------------------------------------
#  Logout
# ------------------------------------------------------------------

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out.', 'info')
    return redirect(url_for('auth.login'))


# ------------------------------------------------------------------
#  Student Registration
# ------------------------------------------------------------------

@auth_bp.route('/register/student', methods=['GET', 'POST'])
def register_student():
    if current_user.is_authenticated:
        return redirect(url_for('auth.home'))

    if request.method == 'POST':
        email   = request.form['email'].strip()
        pwd     = request.form['password']
        name    = request.form['name'].strip()
        roll_no = request.form['roll_no'].strip()
        branch  = request.form.get('branch', '').strip()
        year    = request.form.get('year', '')
        cgpa    = request.form.get('cgpa', '')
        phone   = request.form.get('phone', '').strip()
        skills  = request.form.get('skills', '').strip()
        about   = request.form.get('about', '').strip()

        # Validation
        if not email or not pwd or not name or not roll_no:
            flash('Please fill all required fields.', 'danger')
            return redirect(url_for('auth.register_student'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('auth.register_student'))

        if Student.query.filter_by(roll_no=roll_no).first():
            flash('Roll number already exists.', 'danger')
            return redirect(url_for('auth.register_student'))

        # Create user + student profile
        user = User(email=email, password=hash_password(pwd), role='student')
        sr = Role.query.filter_by(name='student').first()
        if sr:
            user.roles.append(sr)
        db.session.add(user)
        db.session.flush()

        student = Student(
            user_id=user.id, name=name, roll_no=roll_no,
            branch=branch, year=int(year) if year else None,
            cgpa=float(cgpa) if cgpa else None,
            phone=phone, skills=skills, about=about
        )

        # Handle resume upload
        if 'resume' in request.files:
            f = request.files['resume']
            if f and f.filename and allowed_file(f.filename):
                fname = secure_filename(roll_no + '_' + f.filename)
                f.save(os.path.join(current_app.config['UPLOAD_FOLDER'], fname))
                student.resume = fname

        db.session.add(student)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register_student.html')


# ------------------------------------------------------------------
#  Company Registration
# ------------------------------------------------------------------

@auth_bp.route('/register/company', methods=['GET', 'POST'])
def register_company():
    if current_user.is_authenticated:
        return redirect(url_for('auth.home'))

    if request.method == 'POST':
        email    = request.form['email'].strip()
        pwd      = request.form['password']
        name     = request.form['name'].strip()
        industry = request.form.get('industry', '').strip()
        hr_name  = request.form.get('hr_name', '').strip()
        hr_email = request.form.get('hr_email', '').strip()
        hr_phone = request.form.get('hr_phone', '').strip()
        website  = request.form.get('website', '').strip()
        desc     = request.form.get('description', '').strip()

        # Validation
        if not email or not pwd or not name:
            flash('Please fill all required fields.', 'danger')
            return redirect(url_for('auth.register_company'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('auth.register_company'))

        # Create user + company profile (status=pending until admin approves)
        user = User(email=email, password=hash_password(pwd), role='company')
        cr = Role.query.filter_by(name='company').first()
        if cr:
            user.roles.append(cr)
        db.session.add(user)
        db.session.flush()

        company = Company(
            user_id=user.id, name=name, industry=industry,
            hr_name=hr_name, hr_email=hr_email, hr_phone=hr_phone,
            website=website, description=desc, status='pending'
        )
        db.session.add(company)
        db.session.commit()
        flash('Registration submitted! Wait for admin approval.', 'info')
        return redirect(url_for('auth.login'))

    return render_template('register_company.html')


# ------------------------------------------------------------------
#  Serve uploaded files (resumes, CSV exports, etc.)
# ------------------------------------------------------------------

@auth_bp.route('/uploads/<filename>')
@login_required
def get_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
