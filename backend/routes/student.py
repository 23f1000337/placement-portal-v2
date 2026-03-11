"""
Student routes — dashboard, profile, browse drives, applications, history, search, CSV export.
All routes require student role.
"""

import os
from flask import Blueprint, render_template, request, jsonify, current_app, make_response
from flask_security import current_user
from werkzeug.utils import secure_filename
from datetime import date, datetime

from backend.extensions import db, cache
from backend.models import Student, Company, PlacementDrive, Application, Placement
from backend.helpers import student_required, allowed_file

student_bp = Blueprint('student', __name__)


# ==================================================================
#  PAGE ROUTES
# ==================================================================

@student_bp.route('/student/dashboard')
@student_required
def student_dashboard():
    return render_template('student/dashboard.html')


@student_bp.route('/student/profile')
@student_required
def student_profile():
    return render_template('student/profile.html')


@student_bp.route('/student/drives')
@student_required
def browse_drives():
    return render_template('student/drives.html')


@student_bp.route('/student/applications')
@student_required
def my_applications():
    return render_template('student/applications.html')


@student_bp.route('/student/history')
@student_required
def placement_history():
    return render_template('student/history.html')


@student_bp.route('/student/search')
@student_required
def student_search():
    return render_template('student/search.html')


# ==================================================================
#  API ROUTES — JSON data for Vue.js frontend
# ==================================================================

# --- Student info ---

@student_bp.route('/api/student/info')
@student_required
def api_student_info():
    student = current_user.student
    open_drives = PlacementDrive.query.filter_by(status='approved').count()
    my_apps     = Application.query.filter_by(student_id=student.id).count()
    selected    = Application.query.filter_by(student_id=student.id, status='selected').count()

    # Upcoming interviews (interview date in future with status interview/shortlisted)
    upcoming = Application.query.filter(
        Application.student_id == student.id,
        Application.interview_date != None,
        Application.interview_date >= datetime.utcnow(),
        Application.status.in_(['shortlisted', 'interview'])
    ).order_by(Application.interview_date.asc()).all()

    interviews = [{
        'id': a.id, 'drive': a.drive.title, 'company': a.drive.company.name,
        'location': a.drive.location or '',
        'interview_date': a.interview_date.strftime('%d %b %Y'),
        'notes': a.notes or ''
    } for a in upcoming]

    return jsonify({
        'student': {
            'id': student.id, 'name': student.name, 'roll_no': student.roll_no,
            'branch': student.branch or '', 'year': student.year,
            'cgpa': student.cgpa, 'phone': student.phone or '',
            'skills': student.skills or '', 'about': student.about or '',
            'experience': student.experience or '',
            'resume': student.resume, 'email': student.user.email
        },
        'open_drives': open_drives,
        'my_apps': my_apps,
        'selected': selected,
        'interviews': interviews
    })


# --- Profile update (supports both JSON and form-data for file upload) ---

@student_bp.route('/api/student/profile', methods=['PUT'])
@student_required
def api_update_student_profile():
    student = current_user.student

    if request.content_type and 'multipart/form-data' in request.content_type:
        # Form data — used when uploading resume
        student.name   = request.form.get('name', student.name).strip()
        student.branch = request.form.get('branch', '').strip()
        year = request.form.get('year', '')
        student.year   = int(year) if year else student.year
        cgpa = request.form.get('cgpa', '')
        student.cgpa   = float(cgpa) if cgpa else student.cgpa
        student.phone  = request.form.get('phone', '').strip()
        student.skills = request.form.get('skills', '').strip()
        student.about  = request.form.get('about', '').strip()
        student.experience = request.form.get('experience', '').strip()

        # Handle resume file upload
        if 'resume' in request.files:
            f = request.files['resume']
            if f and f.filename and allowed_file(f.filename):
                fname = secure_filename(student.roll_no + '_' + f.filename)
                f.save(os.path.join(current_app.config['UPLOAD_FOLDER'], fname))
                student.resume = fname
    else:
        # JSON data
        data = request.get_json()
        student.name   = data.get('name', student.name).strip()
        student.branch = data.get('branch', '').strip()
        student.year   = int(data['year']) if data.get('year') else student.year
        student.cgpa   = float(data['cgpa']) if data.get('cgpa') else student.cgpa
        student.phone  = data.get('phone', '').strip()
        student.skills = data.get('skills', '').strip()
        student.about  = data.get('about', '').strip()
        student.experience = data.get('experience', '').strip()

    db.session.commit()
    cache.clear()
    return jsonify({'success': True, 'message': 'Profile updated', 'resume': student.resume})


# --- Browse drives (paginated, searchable, with eligibility check) ---

@student_bp.route('/api/student/drives')
@student_required
@cache.cached(timeout=30, query_string=True, key_prefix='student_drives')
def api_student_drives():
    search_query = request.args.get('q', '').strip()
    page     = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # Only show approved drives
    query = PlacementDrive.query.filter_by(status='approved')

    # Search by title, skills, or company name
    if search_query:
        query = query.join(Company).filter(
            (PlacementDrive.title.ilike('%' + search_query + '%')) |
            (PlacementDrive.skills_required.ilike('%' + search_query + '%')) |
            (Company.name.ilike('%' + search_query + '%'))
        )

    pagination = query.order_by(PlacementDrive.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    student = current_user.student
    applied_drive_ids = [a.drive_id for a in Application.query.filter_by(student_id=student.id).all()]

    result = []
    for drive in pagination.items:
        # Check eligibility
        eligible = True
        reasons = []

        if drive.min_cgpa and student.cgpa and student.cgpa < drive.min_cgpa:
            eligible = False
            reasons.append('CGPA below ' + str(drive.min_cgpa))

        if drive.eligible_branches:
            branches = [b.strip().upper() for b in drive.eligible_branches.split(',')]
            if student.branch and student.branch.upper() not in branches:
                eligible = False
                reasons.append('Branch not eligible')

        if drive.eligible_year and student.year and student.year != drive.eligible_year:
            eligible = False
            reasons.append('Year mismatch')

        result.append({
            'id': drive.id, 'title': drive.title, 'company': drive.company.name,
            'location': drive.location or '', 'salary': drive.salary or '',
            'deadline': str(drive.deadline) if drive.deadline else '',
            'description': drive.description or '', 'eligibility': drive.eligibility or '',
            'skills_required': drive.skills_required or '',
            'min_cgpa': drive.min_cgpa, 'eligible_branches': drive.eligible_branches or '',
            'already_applied': drive.id in applied_drive_ids,
            'eligible': eligible, 'reasons': reasons
        })

    return jsonify({
        'items': result, 'total': pagination.total,
        'page': page, 'per_page': per_page, 'pages': pagination.pages
    })


# --- Apply to a drive (with eligibility checks) ---

@student_bp.route('/api/student/apply/<int:id>', methods=['POST'])
@student_required
def api_apply_drive(id):
    drive = PlacementDrive.query.get_or_404(id)
    student = current_user.student

    # Validate
    if drive.status != 'approved':
        return jsonify({'success': False, 'message': 'Drive is not open'}), 400

    if drive.deadline and drive.deadline < date.today():
        return jsonify({'success': False, 'message': 'Deadline has passed'}), 400

    if drive.min_cgpa and student.cgpa and student.cgpa < drive.min_cgpa:
        return jsonify({'success': False, 'message': 'CGPA below minimum requirement'}), 400

    if drive.eligible_branches:
        branches = [b.strip().upper() for b in drive.eligible_branches.split(',')]
        if student.branch and student.branch.upper() not in branches:
            return jsonify({'success': False, 'message': 'Your branch is not eligible'}), 400

    if drive.eligible_year and student.year and student.year != drive.eligible_year:
        return jsonify({'success': False, 'message': 'Graduation year mismatch'}), 400

    # Check if already applied
    existing = Application.query.filter_by(student_id=student.id, drive_id=id).first()
    if existing:
        return jsonify({'success': False, 'message': 'Already applied'}), 400

    new_app = Application(student_id=student.id, drive_id=id)
    db.session.add(new_app)
    db.session.commit()
    cache.clear()
    return jsonify({'success': True, 'message': 'Applied successfully!'})


# --- My applications ---

@student_bp.route('/api/student/applications')
@student_required
@cache.cached(timeout=30, query_string=True, key_prefix='student_applications')
def api_student_applications():
    applications = Application.query.filter_by(
        student_id=current_user.student.id
    ).order_by(Application.applied_on.desc()).all()

    result = [{
        'id': a.id, 'drive': a.drive.title, 'company': a.drive.company.name,
        'location': a.drive.location or '', 'salary': a.drive.salary or '',
        'applied_on': a.applied_on.strftime('%d %b %Y'),
        'status': a.status,
        'interview_date': a.interview_date.strftime('%d %b %Y') if a.interview_date else '',
        'notes': a.notes or ''
    } for a in applications]

    return jsonify(result)


# --- Placement history (selected/rejected/placed results) ---

@student_bp.route('/api/student/history')
@student_required
@cache.cached(timeout=30, query_string=True, key_prefix='student_history')
def api_student_history():
    applications = Application.query.filter_by(
        student_id=current_user.student.id
    ).filter(
        Application.status.in_(['selected', 'rejected', 'placed'])
    ).order_by(Application.applied_on.desc()).all()

    result = [{
        'id': a.id, 'company': a.drive.company.name,
        'role': a.drive.title, 'salary': a.drive.salary or '',
        'status': a.status,
        'applied_on': a.applied_on.strftime('%d %b %Y'),
        'notes': a.notes or ''
    } for a in applications]

    return jsonify(result)


# --- Offer letter / Placement confirmation download (HTML) ---

@student_bp.route('/api/student/offer-letter/<int:app_id>')
@student_required
def api_offer_letter(app_id):
    app_record = Application.query.get_or_404(app_id)

    if app_record.student_id != current_user.student.id:
        return jsonify({'success': False, 'message': 'Access denied'}), 403

    if app_record.status not in ('selected', 'placed'):
        return jsonify({'success': False, 'message': 'Download available for selected/placed status only'}), 400

    student = current_user.student
    company = app_record.drive.company
    drive   = app_record.drive
    today   = date.today().strftime('%d %B %Y')
    is_placed = app_record.status == 'placed'

    title = 'Placement Confirmation' if is_placed else 'Offer Letter'
    body_text = (
        f'This is to confirm that <strong>{student.name}</strong> (Roll No: {student.roll_no}) '
        f'has been placed at <strong>{company.name}</strong> for the position of '
        f'<strong>{drive.title}</strong>.'
    ) if is_placed else (
        f'We are pleased to inform you that you have been selected for the position of '
        f'<strong>{drive.title}</strong> at <strong>{company.name}</strong>.'
    )
    closing = (
        'Congratulations on your placement! We welcome you to the team.'
    ) if is_placed else (
        'We look forward to having you on our team. Please confirm your acceptance at the earliest.'
    )

    html = f"""<!DOCTYPE html>
<html><head><title>{title}</title>
<style>
body {{ font-family: 'Georgia', serif; margin: 40px; color: #333; }}
.header {{ text-align: center; border-bottom: 2px solid #333; padding-bottom: 15px; margin-bottom: 30px; }}
.header h1 {{ margin: 0; font-size: 28px; }}
.header p {{ margin: 5px 0; color: #666; }}
.content {{ line-height: 1.8; font-size: 14px; }}
.footer {{ margin-top: 50px; }}
.signature {{ margin-top: 40px; }}
</style></head><body>
<div class="header">
    <h1>{company.name}</h1>
    <p>{company.industry or title}</p>
</div>
<div class="content">
    <p><strong>Date:</strong> {today}</p>
    <p><strong>To:</strong> {student.name}<br>
       Roll No: {student.roll_no}<br>
       Branch: {student.branch or 'N/A'}</p>
    <p>Dear {student.name},</p>
    <p>{body_text}</p>
    <p><strong>Position:</strong> {drive.title}<br>
       <strong>Location:</strong> {drive.location or 'To be communicated'}<br>
       <strong>Compensation:</strong> {drive.salary or 'As discussed'}</p>
    <p>{closing}</p>
    <div class="footer">
        <p>Best regards,</p>
        <div class="signature">
            <p><strong>{company.hr_name or 'HR Department'}</strong><br>
               {company.name}<br>
               {company.hr_email or ''}</p>
        </div>
    </div>
</div>
</body></html>"""

    filename = f'placement_confirmation_{student.roll_no}_{drive.id}.html' if is_placed else f'offer_letter_{student.roll_no}_{drive.id}.html'
    response = make_response(html)
    response.headers['Content-Type'] = 'text/html'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response


# --- Search drives and companies ---

@student_bp.route('/api/student/search')
@student_required
@cache.cached(timeout=30, query_string=True, key_prefix='student_search')
def api_student_search():
    q     = request.args.get('q', '').strip()
    stype = request.args.get('type', 'drive')

    if not q:
        return jsonify({'drives': [], 'companies': []})

    if stype == 'company':
        companies = Company.query.filter(
            Company.status == 'approved',
            (Company.name.ilike('%' + q + '%')) |
            (Company.industry.ilike('%' + q + '%'))
        ).all()

        return jsonify({
            'companies': [{
                'id': c.id, 'name': c.name, 'industry': c.industry or '',
                'website': c.website or '', 'hr_name': c.hr_name or '',
                'drives_count': len([d for d in c.drives if d.status == 'approved'])
            } for c in companies],
            'drives': []
        })
    else:
        drives = PlacementDrive.query.join(Company).filter(
            PlacementDrive.status == 'approved',
            (PlacementDrive.title.ilike('%' + q + '%')) |
            (PlacementDrive.skills_required.ilike('%' + q + '%')) |
            (Company.name.ilike('%' + q + '%'))
        ).all()

        return jsonify({
            'drives': [{
                'id': d.id, 'title': d.title, 'company': d.company.name,
                'location': d.location or '', 'salary': d.salary or '',
                'deadline': str(d.deadline) if d.deadline else '',
                'skills_required': d.skills_required or ''
            } for d in drives],
            'companies': []
        })


# --- CSV Export (async with Celery or sync fallback) ---

@student_bp.route('/api/student/export-csv', methods=['POST'])
@student_required
def api_export_csv():
    from backend.tasks import export_student_csv

    # Try async export via Celery (needs Redis)
    try:
        import redis
        from backend.config import CACHE_REDIS_URL
        r = redis.Redis.from_url(CACHE_REDIS_URL, socket_connect_timeout=2)
        r.ping()
        task = export_student_csv.delay(current_user.student.id)
        return jsonify({'success': True, 'message': 'Export started', 'task_id': task.id})
    except Exception:
        # Redis/Celery not available — run synchronously
        filename = export_student_csv(current_user.student.id)
        return jsonify({'success': True, 'message': 'Export complete', 'task_id': None, 'filename': filename})


@student_bp.route('/api/student/export-status/<task_id>')
@student_required
def api_export_status(task_id):
    """Check the status of an async CSV export task."""
    from backend.tasks import export_student_csv

    try:
        result = export_student_csv.AsyncResult(task_id)
        if result.ready():
            if result.successful():
                return jsonify({'ready': True, 'filename': result.result})
            return jsonify({'ready': True, 'filename': None, 'error': 'Export failed'})
        return jsonify({'ready': False})
    except Exception:
        return jsonify({'ready': True, 'filename': None, 'error': 'Cannot check status'})
