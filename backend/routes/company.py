import os
import csv
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_security import login_required, current_user
from datetime import datetime

from backend.extensions import db, cache
from backend.models import Company, PlacementDrive, Application, Student
from backend.helpers import company_required

company_bp = Blueprint('company', __name__)


#  PAGE ROUTES

@company_bp.route('/company/pending')
@login_required
def company_pending():
    """Show pending/rejected status page for unapproved companies."""
    if current_user.role != 'company':
        return redirect(url_for('auth.home'))
    return render_template('company/pending.html', status=current_user.company.status)


@company_bp.route('/company/dashboard')
@company_required
def company_dashboard():
    return render_template('company/dashboard.html')


@company_bp.route('/company/profile')
@company_required
def company_profile():
    return render_template('company/profile.html')


@company_bp.route('/company/drive/create')
@company_required
def create_drive():
    return render_template('company/create_drive.html')


@company_bp.route('/company/drive/<int:id>/edit')
@company_required
def edit_drive(id):
    drive = PlacementDrive.query.get_or_404(id)
    if drive.company_id != current_user.company.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('company.company_dashboard'))
    return render_template('company/edit_drive.html', drive_id=id)


@company_bp.route('/company/drive/<int:id>/applications')
@company_required
def view_applications(id):
    drive = PlacementDrive.query.get_or_404(id)
    if drive.company_id != current_user.company.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('company.company_dashboard'))
    return render_template('company/applications.html', drive_id=id)



#  API ROUTES 

# Company info
@company_bp.route('/api/company/info')
@company_required
@cache.cached(timeout=60, key_prefix='company_info')
def api_company_info():
    company = current_user.company
    drives = PlacementDrive.query.filter_by(company_id=company.id).all()
    total_apps = sum(len(d.applications) for d in drives)

    return jsonify({
        'company': {
            'id': company.id, 'name': company.name, 'industry': company.industry or '',
            'hr_name': company.hr_name or '', 'hr_email': company.hr_email or '',
            'hr_phone': company.hr_phone or '', 'website': company.website or '',
            'description': company.description or '', 'status': company.status
        },
        'total_drives': len(drives),
        'total_apps': total_apps
    })


# Profile update
@company_bp.route('/api/company/profile', methods=['PUT'])
@company_required
def api_update_company_profile():
    company = current_user.company
    data = request.get_json()

    company.name        = data.get('name', company.name).strip()
    company.industry    = data.get('industry', '').strip()
    company.hr_name     = data.get('hr_name', '').strip()
    company.hr_email    = data.get('hr_email', '').strip()
    company.hr_phone    = data.get('hr_phone', '').strip()
    company.website     = data.get('website', '').strip()
    company.description = data.get('description', '').strip()

    db.session.commit()
    cache.clear()
    return jsonify({'success': True, 'message': 'Profile updated'})


# Drives: list, create, read, update, close, delete
@company_bp.route('/api/company/drives')
@company_required
@cache.cached(timeout=30, key_prefix='company_drives')
def api_company_drives():
    drives = PlacementDrive.query.filter_by(company_id=current_user.company.id).all()

    result = [{
        'id': d.id, 'title': d.title, 'description': d.description or '',
        'location': d.location or '', 'salary': d.salary or '',
        'deadline': str(d.deadline) if d.deadline else '',
        'status': d.status, 'apps_count': len(d.applications),
        'eligibility': d.eligibility or '', 'skills_required': d.skills_required or '',
        'min_cgpa': d.min_cgpa, 'eligible_branches': d.eligible_branches or '',
        'eligible_year': d.eligible_year
    } for d in drives]

    return jsonify(result)


@company_bp.route('/api/company/drives', methods=['POST'])
@company_required
def api_create_drive():
    data = request.get_json()
    title = data.get('title', '').strip()
    if not title:
        return jsonify({'success': False, 'message': 'Job title is required'}), 400

    deadline = None
    if data.get('deadline'):
        deadline = datetime.strptime(data['deadline'], '%Y-%m-%d').date()

    drive = PlacementDrive(
        company_id=current_user.company.id,
        title=title,
        description=data.get('description', '').strip(),
        eligibility=data.get('eligibility', '').strip(),
        eligible_branches=data.get('eligible_branches', '').strip(),
        min_cgpa=float(data.get('min_cgpa', 0) or 0),
        eligible_year=int(data['eligible_year']) if data.get('eligible_year') else None,
        skills_required=data.get('skills_required', '').strip(),
        salary=data.get('salary', '').strip(),
        location=data.get('location', '').strip(),
        deadline=deadline,
        status='pending'
    )
    db.session.add(drive)
    db.session.commit()
    cache.clear()
    return jsonify({'success': True, 'message': 'Drive created! Waiting for admin approval.'})


@company_bp.route('/api/company/drive/<int:id>', methods=['GET'])
@company_required
def api_get_drive(id):
    drive = PlacementDrive.query.get_or_404(id)
    if drive.company_id != current_user.company.id:
        return jsonify({'success': False, 'message': 'Access denied'}), 403

    return jsonify({
        'id': drive.id, 'title': drive.title, 'description': drive.description or '',
        'location': drive.location or '', 'salary': drive.salary or '',
        'deadline': str(drive.deadline) if drive.deadline else '',
        'eligibility': drive.eligibility or '', 'skills_required': drive.skills_required or '',
        'min_cgpa': drive.min_cgpa, 'eligible_branches': drive.eligible_branches or '',
        'eligible_year': drive.eligible_year, 'status': drive.status
    })


@company_bp.route('/api/company/drive/<int:id>', methods=['PUT'])
@company_required
def api_update_drive(id):
    drive = PlacementDrive.query.get_or_404(id)
    if drive.company_id != current_user.company.id:
        return jsonify({'success': False, 'message': 'Access denied'}), 403

    data = request.get_json()
    drive.title             = data.get('title', drive.title).strip()
    drive.description       = data.get('description', '').strip()
    drive.eligibility       = data.get('eligibility', '').strip()
    drive.eligible_branches = data.get('eligible_branches', '').strip()
    drive.min_cgpa          = float(data.get('min_cgpa', 0) or 0)
    drive.eligible_year     = int(data['eligible_year']) if data.get('eligible_year') else None
    drive.skills_required   = data.get('skills_required', '').strip()
    drive.salary            = data.get('salary', '').strip()
    drive.location          = data.get('location', '').strip()
    if data.get('deadline'):
        drive.deadline = datetime.strptime(data['deadline'], '%Y-%m-%d').date()

    db.session.commit()
    cache.clear()
    return jsonify({'success': True, 'message': 'Drive updated'})


@company_bp.route('/api/company/drive/<int:id>/close', methods=['POST'])
@company_required
def api_close_drive(id):
    drive = PlacementDrive.query.get_or_404(id)
    if drive.company_id != current_user.company.id:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    drive.status = 'closed'
    db.session.commit()
    cache.clear()
    return jsonify({'success': True, 'message': 'Drive closed'})


@company_bp.route('/api/company/drive/<int:id>', methods=['DELETE'])
@company_required
def api_delete_drive(id):
    drive = PlacementDrive.query.get_or_404(id)
    if drive.company_id != current_user.company.id:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    Application.query.filter_by(drive_id=drive.id).delete()
    db.session.delete(drive)
    db.session.commit()
    cache.clear()
    return jsonify({'success': True, 'message': 'Drive deleted'})


# Student detail
@company_bp.route('/api/company/student/<int:id>')
@company_required
def api_company_student_detail(id):
    """View a student's profile — only if they have applied to one of this company's drives."""
    student = Student.query.get_or_404(id)
    company = current_user.company
    # Verify the student has applied to at least one of this company's drives
    has_applied = Application.query.join(PlacementDrive).filter(
        Application.student_id == student.id,
        PlacementDrive.company_id == company.id
    ).first()
    if not has_applied:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    return jsonify({
        'student': {
            'id': student.id, 'name': student.name, 'roll_no': student.roll_no,
            'branch': student.branch or '', 'year': student.year,
            'cgpa': student.cgpa, 'phone': student.phone or '',
            'skills': student.skills or '', 'about': student.about or '',
            'experience': student.experience or '',
            'resume': student.resume, 'email': student.user.email
        }
    })


# Applications: view all for a drive, update status 
@company_bp.route('/api/company/drive/<int:id>/applications')
@company_required
@cache.cached(timeout=30, query_string=True, key_prefix='company_drive_apps')
def api_drive_applications(id):
    drive = PlacementDrive.query.get_or_404(id)
    if drive.company_id != current_user.company.id:
        return jsonify({'success': False, 'message': 'Access denied'}), 403

    applications = Application.query.filter_by(drive_id=id).all()

    items = [{
        'id': a.id, 'student_id': a.student.id, 'student_name': a.student.name,
        'roll_no': a.student.roll_no, 'branch': a.student.branch or '',
        'cgpa': a.student.cgpa, 'resume': a.student.resume,
        'applied_on': a.applied_on.strftime('%d %b %Y'),
        'status': a.status,
        'interview_date': a.interview_date.strftime('%Y-%m-%d') if a.interview_date else '',
        'notes': a.notes or ''
    } for a in applications]

    return jsonify({
        'drive': {'id': drive.id, 'title': drive.title},
        'applications': items
    })


@company_bp.route('/api/company/application/<int:id>/status', methods=['POST'])
@company_required
def api_update_app_status(id):
    """Update an application's status, interview date, and/or notes."""
    app_record = Application.query.get_or_404(id)
    drive = PlacementDrive.query.get(app_record.drive_id)
    if drive.company_id != current_user.company.id:
        return jsonify({'success': False, 'message': 'Access denied'}), 403

    data = request.get_json()
    new_status = data.get('status', '')

    # Only allow valid status transitions
    valid_statuses = ['applied', 'shortlisted', 'interview', 'selected', 'rejected', 'placed']
    if new_status in valid_statuses:
        app_record.status = new_status

    if data.get('interview_date'):
        app_record.interview_date = datetime.strptime(data['interview_date'], '%Y-%m-%d')

    if 'notes' in data:
        app_record.notes = data['notes'].strip()

    db.session.commit()
    cache.clear()
    return jsonify({'success': True, 'message': 'Status updated to ' + new_status})


# CSV Export 
@company_bp.route('/api/company/export-csv', methods=['POST'])
@company_required
def api_company_export_csv():
    """Export all applications across the company's drives as a CSV file."""
    from backend.tasks import export_company_csv

    company = current_user.company

    # Try async export via Celery (needs Redis)
    try:
        import redis
        from backend.config import CACHE_REDIS_URL
        r = redis.Redis.from_url(CACHE_REDIS_URL, socket_connect_timeout=2)
        r.ping()
        task = export_company_csv.delay(company.id)
        return jsonify({'success': True, 'message': 'Export started', 'task_id': task.id})
    except Exception:
        # Redis/Celery not available — run synchronously
        filename = export_company_csv(company.id)
        return jsonify({'success': True, 'message': 'Export complete', 'task_id': None, 'filename': filename})


@company_bp.route('/api/company/export-status/<task_id>')
@company_required
def api_company_export_status(task_id):
    """Check the status of an async CSV export task."""
    from backend.tasks import export_company_csv

    try:
        result = export_company_csv.AsyncResult(task_id)
        if result.ready():
            if result.successful():
                return jsonify({'ready': True, 'filename': result.result})
            return jsonify({'ready': True, 'filename': None, 'error': 'Export failed'})
        return jsonify({'ready': False})
    except Exception:
        return jsonify({'ready': True, 'filename': None, 'error': 'Cannot check status'})
