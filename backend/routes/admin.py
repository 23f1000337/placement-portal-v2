"""
Admin routes — dashboard, manage companies/students/drives/applications, search.
All routes require admin role.
"""

from flask import Blueprint, render_template, request, jsonify
from flask_security import current_user

from backend.extensions import db, cache
from backend.models import User, Student, Company, PlacementDrive, Application
from backend.helpers import admin_required

admin_bp = Blueprint('admin', __name__)


# ==================================================================
#  PAGE ROUTES — serve HTML templates
# ==================================================================

@admin_bp.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    return render_template('admin/dashboard.html')


@admin_bp.route('/admin/companies')
@admin_required
def admin_companies():
    return render_template('admin/companies.html')


@admin_bp.route('/admin/students')
@admin_required
def admin_students():
    return render_template('admin/students.html')


@admin_bp.route('/admin/drives')
@admin_required
def admin_drives():
    return render_template('admin/drives.html')


@admin_bp.route('/admin/applications')
@admin_required
def admin_applications():
    return render_template('admin/applications.html')


@admin_bp.route('/admin/search')
@admin_required
def admin_search():
    return render_template('admin/search.html')


# ==================================================================
#  API ROUTES — return JSON data for Vue.js frontend
# ==================================================================

# --- Dashboard stats (cached 60s) ---

@admin_bp.route('/api/admin/stats')
@admin_required
@cache.cached(timeout=60, key_prefix='admin_stats')
def api_admin_stats():
    return jsonify({
        'students':          Student.query.count(),
        'companies':         Company.query.count(),
        'drives':            PlacementDrive.query.count(),
        'applications':      Application.query.count(),
        'pending_companies': Company.query.filter_by(status='pending').count(),
        'pending_drives':    PlacementDrive.query.filter_by(status='pending').count(),
        'selected':          Application.query.filter_by(status='selected').count(),
    })


# --- Companies: list, approve, reject, blacklist, delete ---

@admin_bp.route('/api/admin/companies')
@admin_required
@cache.cached(timeout=30, query_string=True, key_prefix='admin_companies')
def api_admin_companies():
    status   = request.args.get('status', 'all')
    page     = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    query = Company.query
    if status != 'all':
        query = query.filter_by(status=status)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    items = [{
        'id': c.id, 'name': c.name, 'industry': c.industry or '',
        'hr_name': c.hr_name or '', 'hr_email': c.hr_email or '',
        'status': c.status, 'is_blacklisted': c.user.is_blacklisted,
        'drives_count': len(c.drives)
    } for c in pagination.items]

    return jsonify({
        'items': items, 'total': pagination.total,
        'page': page, 'per_page': per_page, 'pages': pagination.pages
    })


@admin_bp.route('/api/admin/company/<int:id>/approve', methods=['POST'])
@admin_required
def api_approve_company(id):
    company = Company.query.get_or_404(id)
    company.status = 'approved'
    db.session.commit()
    cache.clear()
    return jsonify({'success': True, 'message': company.name + ' approved'})


@admin_bp.route('/api/admin/company/<int:id>/reject', methods=['POST'])
@admin_required
def api_reject_company(id):
    company = Company.query.get_or_404(id)
    company.status = 'rejected'
    db.session.commit()
    cache.clear()
    return jsonify({'success': True, 'message': company.name + ' rejected'})


@admin_bp.route('/api/admin/company/<int:id>/blacklist', methods=['POST'])
@admin_required
def api_blacklist_company(id):
    company = Company.query.get_or_404(id)
    company.user.is_blacklisted = not company.user.is_blacklisted
    company.user.active = not company.user.is_blacklisted
    db.session.commit()
    cache.clear()
    status = 'blacklisted' if company.user.is_blacklisted else 'unblacklisted'
    return jsonify({'success': True, 'message': company.name + ' ' + status})


@admin_bp.route('/api/admin/company/<int:id>', methods=['DELETE'])
@admin_required
def api_delete_company(id):
    company = Company.query.get_or_404(id)
    # Delete related data: applications → drives → company → user
    for drive in company.drives:
        Application.query.filter_by(drive_id=drive.id).delete()
    PlacementDrive.query.filter_by(company_id=company.id).delete()
    user = company.user
    db.session.delete(company)
    db.session.delete(user)
    db.session.commit()
    cache.clear()
    return jsonify({'success': True, 'message': 'Company deleted'})


# --- Students: list, detail, blacklist, delete ---

@admin_bp.route('/api/admin/student/<int:id>')
@admin_required
def api_admin_student_detail(id):
    """Get full profile + application history for a single student."""
    student = Student.query.get_or_404(id)
    apps = Application.query.filter_by(student_id=student.id).order_by(
        Application.applied_on.desc()
    ).all()
    return jsonify({
        'student': {
            'id': student.id, 'name': student.name, 'roll_no': student.roll_no,
            'branch': student.branch or '', 'year': student.year,
            'cgpa': student.cgpa, 'phone': student.phone or '',
            'skills': student.skills or '', 'about': student.about or '',
            'experience': student.experience or '',
            'resume': student.resume, 'email': student.user.email,
            'is_blacklisted': student.user.is_blacklisted
        },
        'applications': [{
            'id': a.id, 'drive': a.drive.title, 'company': a.drive.company.name,
            'status': a.status, 'applied_on': a.applied_on.strftime('%d %b %Y'),
            'interview_date': a.interview_date.strftime('%d %b %Y') if a.interview_date else '',
            'notes': a.notes or ''
        } for a in apps]
    })


@admin_bp.route('/api/admin/students')
@admin_required
@cache.cached(timeout=30, query_string=True, key_prefix='admin_students')
def api_admin_students():
    page     = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    pagination = Student.query.paginate(page=page, per_page=per_page, error_out=False)

    items = [{
        'id': s.id, 'name': s.name, 'roll_no': s.roll_no,
        'branch': s.branch or '', 'year': s.year,
        'cgpa': s.cgpa, 'phone': s.phone or '',
        'email': s.user.email, 'is_blacklisted': s.user.is_blacklisted,
        'resume': s.resume, 'apps_count': len(s.applications)
    } for s in pagination.items]

    return jsonify({
        'items': items, 'total': pagination.total,
        'page': page, 'per_page': per_page, 'pages': pagination.pages
    })


@admin_bp.route('/api/admin/student/<int:id>/blacklist', methods=['POST'])
@admin_required
def api_blacklist_student(id):
    student = Student.query.get_or_404(id)
    student.user.is_blacklisted = not student.user.is_blacklisted
    student.user.active = not student.user.is_blacklisted
    db.session.commit()
    cache.clear()
    status = 'blacklisted' if student.user.is_blacklisted else 'unblacklisted'
    return jsonify({'success': True, 'message': student.name + ' ' + status})


@admin_bp.route('/api/admin/student/<int:id>', methods=['DELETE'])
@admin_required
def api_delete_student(id):
    student = Student.query.get_or_404(id)
    Application.query.filter_by(student_id=student.id).delete()
    user = student.user
    db.session.delete(student)
    db.session.delete(user)
    db.session.commit()
    cache.clear()
    return jsonify({'success': True, 'message': 'Student deleted'})


# --- Drives: list, approve, reject ---

@admin_bp.route('/api/admin/drives')
@admin_required
@cache.cached(timeout=30, query_string=True, key_prefix='admin_drives')
def api_admin_drives():
    status   = request.args.get('status', 'all')
    page     = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    query = PlacementDrive.query
    if status != 'all':
        query = query.filter_by(status=status)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    items = [{
        'id': d.id, 'title': d.title, 'company': d.company.name,
        'location': d.location or '', 'salary': d.salary or '',
        'deadline': str(d.deadline) if d.deadline else '',
        'status': d.status, 'apps_count': len(d.applications),
        'min_cgpa': d.min_cgpa, 'eligible_branches': d.eligible_branches or ''
    } for d in pagination.items]

    return jsonify({
        'items': items, 'total': pagination.total,
        'page': page, 'per_page': per_page, 'pages': pagination.pages
    })


@admin_bp.route('/api/admin/drive/<int:id>/approve', methods=['POST'])
@admin_required
def api_approve_drive(id):
    drive = PlacementDrive.query.get_or_404(id)
    drive.status = 'approved'
    db.session.commit()
    cache.clear()
    return jsonify({'success': True, 'message': drive.title + ' approved'})


@admin_bp.route('/api/admin/drive/<int:id>/reject', methods=['POST'])
@admin_required
def api_reject_drive(id):
    drive = PlacementDrive.query.get_or_404(id)
    drive.status = 'rejected'
    db.session.commit()
    cache.clear()
    return jsonify({'success': True, 'message': drive.title + ' rejected'})


@admin_bp.route('/api/admin/drive/<int:id>/close', methods=['POST'])
@admin_required
def api_close_drive(id):
    drive = PlacementDrive.query.get_or_404(id)
    drive.status = 'closed'
    db.session.commit()
    cache.clear()
    return jsonify({'success': True, 'message': drive.title + ' closed'})


@admin_bp.route('/api/admin/drive/<int:id>', methods=['DELETE'])
@admin_required
def api_delete_drive(id):
    drive = PlacementDrive.query.get_or_404(id)
    Application.query.filter_by(drive_id=drive.id).delete()
    db.session.delete(drive)
    db.session.commit()
    cache.clear()
    return jsonify({'success': True, 'message': 'Drive deleted'})


# --- Applications: list, update status, delete ---

@admin_bp.route('/api/admin/applications')
@admin_required
@cache.cached(timeout=30, query_string=True, key_prefix='admin_applications')
def api_admin_applications():
    page     = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status   = request.args.get('status', 'all')

    query = Application.query
    if status != 'all':
        query = query.filter_by(status=status)

    pagination = query.order_by(
        Application.applied_on.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    items = [{
        'id': a.id, 'student': a.student.name, 'roll_no': a.student.roll_no,
        'drive': a.drive.title, 'company': a.drive.company.name,
        'applied_on': a.applied_on.strftime('%d %b %Y'),
        'status': a.status,
        'interview_date': a.interview_date.strftime('%d %b %Y') if a.interview_date else ''
    } for a in pagination.items]

    return jsonify({
        'items': items, 'total': pagination.total,
        'page': page, 'per_page': per_page, 'pages': pagination.pages
    })


@admin_bp.route('/api/admin/application/<int:id>/status', methods=['POST'])
@admin_required
def api_update_application_status(id):
    app_record = Application.query.get_or_404(id)
    data = request.get_json()
    new_status = data.get('status', '').strip()
    valid = ['applied', 'shortlisted', 'interview', 'selected', 'rejected', 'placed']
    if new_status not in valid:
        return jsonify({'success': False, 'message': 'Invalid status'}), 400
    app_record.status = new_status
    db.session.commit()
    cache.clear()
    return jsonify({'success': True, 'message': 'Status updated to ' + new_status})


@admin_bp.route('/api/admin/application/<int:id>', methods=['DELETE'])
@admin_required
def api_delete_application(id):
    app_record = Application.query.get_or_404(id)
    db.session.delete(app_record)
    db.session.commit()
    cache.clear()
    return jsonify({'success': True, 'message': 'Application deleted'})


# --- Search: students (by name/roll/branch/phone) or companies (by name/industry) ---

@admin_bp.route('/api/admin/search')
@admin_required
@cache.cached(timeout=30, query_string=True, key_prefix='admin_search')
def api_admin_search():
    q     = request.args.get('q', '').strip()
    stype = request.args.get('type', 'student')

    if not q:
        return jsonify({'students': [], 'companies': []})

    if stype == 'student':
        results = Student.query.filter(
            (Student.name.ilike('%' + q + '%')) |
            (Student.roll_no.ilike('%' + q + '%')) |
            (Student.branch.ilike('%' + q + '%')) |
            (Student.phone.ilike('%' + q + '%'))
        ).all()

        return jsonify({
            'students': [{
                'id': s.id, 'name': s.name, 'roll_no': s.roll_no,
                'branch': s.branch or '', 'cgpa': s.cgpa, 'phone': s.phone or '',
                'email': s.user.email, 'is_blacklisted': s.user.is_blacklisted
            } for s in results],
            'companies': []
        })
    else:
        results = Company.query.filter(
            (Company.name.ilike('%' + q + '%')) |
            (Company.industry.ilike('%' + q + '%'))
        ).all()

        return jsonify({
            'students': [],
            'companies': [{
                'id': c.id, 'name': c.name, 'industry': c.industry or '',
                'hr_name': c.hr_name or '', 'status': c.status,
                'is_blacklisted': c.user.is_blacklisted
            } for c in results]
        })
