from functools import wraps
from flask import redirect, url_for, flash
from flask_security import login_required, current_user


# Allowed resume file types
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}


def allowed_file(filename):
    """Check if a filename has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


#  Role-based access decorators

def admin_required(f):
    """Only allow users with role='admin'."""
    @wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        if current_user.role != 'admin':
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return wrapper


def company_required(f):
    """Only allow approved companies."""
    @wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        if current_user.role != 'company':
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.login'))
        if current_user.company.status != 'approved':
            return redirect(url_for('company.company_pending'))
        return f(*args, **kwargs)
    return wrapper


def student_required(f):
    """Only allow users with role='student'."""
    @wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        if current_user.role != 'student':
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return wrapper
