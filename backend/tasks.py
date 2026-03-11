"""
Celery background tasks — email notifications, reminders, reports, CSV exports.
These run asynchronously when Redis + Celery worker is available,
or fall back to synchronous execution otherwise.
"""

import os
import csv
import threading
from datetime import datetime, date, timedelta

from flask import render_template
from backend.extensions import celery, mail
from backend.models import db, User, Student, Company, PlacementDrive, Application


# ------------------------------------------------------------------
#  Email notification helper
# ------------------------------------------------------------------

def _send_notification(to, subject, body, is_html=False):
    """Send a notification via email (non-blocking) + always log to console."""

    # Always print to console as a fallback
    print(f"\n{'=' * 50}")
    print(f"NOTIFICATION -> To: {to} | Subject: {subject}")
    print(f"{'=' * 50}\n")

    # Try sending email via Flask-Mail in a background thread
    try:
        from flask import current_app
        from flask_mail import Message

        username = current_app.config.get('MAIL_USERNAME', '')
        password = current_app.config.get('MAIL_PASSWORD', '')
        server   = current_app.config.get('MAIL_SERVER', '')

        # Only send email if SMTP is properly configured
        if username and password and server and server != 'localhost':
            msg = Message(subject, recipients=[to])
            if is_html:
                msg.html = body
            else:
                msg.body = body

            app = current_app._get_current_object()

            def _do_send():
                try:
                    with app.app_context():
                        mail.send(msg)
                    print(f"  [EMAIL] Sent to {to}")
                except Exception as e:
                    print(f"  [EMAIL] Failed: {e}")

            # Send in a thread with 10s timeout so it doesn't block
            t = threading.Thread(target=_do_send, daemon=True)
            t.start()
            t.join(timeout=10)
            if t.is_alive():
                print(f"  [EMAIL] Sending in background (SMTP slow)")
        else:
            print(f"  [EMAIL] Skipped — SMTP not configured")
    except Exception as e:
        print(f"  [EMAIL] Failed: {e}")


# ------------------------------------------------------------------
#  Task 1: Daily reminders — deadlines + upcoming interviews
# ------------------------------------------------------------------

@celery.task(name='backend.tasks.send_daily_reminders')
def send_daily_reminders():
    """Remind students about drives closing soon and upcoming interviews."""

    two_days_later = date.today() + timedelta(days=2)

    # Find drives with deadlines in the next 2 days
    closing_soon = PlacementDrive.query.filter(
        PlacementDrive.status == 'approved',
        PlacementDrive.deadline <= two_days_later,
        PlacementDrive.deadline >= date.today()
    ).all()

    students = Student.query.all()
    count = 0

    for student in students:
        # Part 1: Deadline reminders (drives they haven't applied to yet)
        already_applied = [a.drive_id for a in student.applications]
        unapplied_closing = [d for d in closing_soon if d.id not in already_applied]

        # Part 2: Interview reminders (interviews within 2 days)
        upcoming_interviews = [
            a for a in student.applications
            if a.interview_date
            and a.interview_date.date() >= date.today()
            and a.interview_date.date() <= two_days_later
        ]

        # Send combined notification if there's anything to say
        if unapplied_closing or upcoming_interviews:
            html = render_template('email/daily_reminder.html',
                student_name=student.name,
                closing_drives=[{
                    'title': d.title, 'company': d.company.name,
                    'deadline': d.deadline
                } for d in unapplied_closing],
                interviews=[{
                    'title': a.drive.title, 'company': a.drive.company.name,
                    'date': a.interview_date.strftime('%d %b %Y')
                } for a in upcoming_interviews]
            )
            _send_notification(student.user.email, 'Placement Reminder', html, is_html=True)
            count += 1

    return f'Reminders sent to {count} students'


# ------------------------------------------------------------------
#  Task 2: Monthly placement report — sent to admin
# ------------------------------------------------------------------

@celery.task(name='backend.tasks.send_monthly_report')
def send_monthly_report():
    """Generate a monthly HTML report and email it to the admin."""

    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Gather stats for this month
    drives_count    = PlacementDrive.query.filter(PlacementDrive.created_at >= month_start).count()
    apps_count      = Application.query.filter(Application.applied_on >= month_start).count()
    selected_count  = Application.query.filter_by(status='selected').count()
    total_students  = Student.query.count()
    total_companies = Company.query.count()

    # Build HTML email from template
    html = render_template('email/monthly_report.html',
        month_year=now.strftime('%B %Y'),
        drives_count=drives_count,
        apps_count=apps_count,
        selected_count=selected_count,
        total_students=total_students,
        total_companies=total_companies,
        generated_at=now.strftime('%d %B %Y at %I:%M %p')
    )

    admin = User.query.filter_by(role='admin').first()
    if admin:
        _send_notification(
            admin.email,
            f'Monthly Placement Report — {now.strftime("%B %Y")}',
            html,
            is_html=True
        )

    return 'Monthly report generated and sent'


# ------------------------------------------------------------------
#  Task 3: Export student's application history as CSV
# ------------------------------------------------------------------

@celery.task(name='backend.tasks.export_student_csv')
def export_student_csv(student_id):
    """Create a CSV file of a student's applications and notify them."""

    student = Student.query.get(student_id)
    if not student:
        return 'Student not found'

    applications = Application.query.filter_by(student_id=student_id).all()

    # Generate unique filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'export_{student.roll_no}_{timestamp}.csv'

    from backend.config import UPLOAD_FOLDER
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    # Write CSV file
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Student ID', 'Roll No', 'Company Name', 'Drive Title',
            'Status', 'Applied On', 'Interview Date'
        ])
        for app_record in applications:
            writer.writerow([
                student.id,
                student.roll_no,
                app_record.drive.company.name,
                app_record.drive.title,
                app_record.status,
                app_record.applied_on.strftime('%Y-%m-%d'),
                app_record.interview_date.strftime('%Y-%m-%d') if app_record.interview_date else '-'
            ])

    # Notify student that export is ready
    html = render_template('email/export_ready.html',
        student_name=student.name, filename=filename
    )
    _send_notification(student.user.email, 'CSV Export Ready', html, is_html=True)

    return filename


# ------------------------------------------------------------------
#  Task 4: Export company's application data as CSV
# ------------------------------------------------------------------

@celery.task(name='backend.tasks.export_company_csv')
def export_company_csv(company_id):
    """Create a CSV file of all applications across a company's drives."""

    company = Company.query.get(company_id)
    if not company:
        return 'Company not found'

    drives = PlacementDrive.query.filter_by(company_id=company_id).all()

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'company_export_{company_id}_{timestamp}.csv'

    from backend.config import UPLOAD_FOLDER
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Drive Title', 'Student Name', 'Roll No', 'Branch',
            'CGPA', 'Status', 'Applied On', 'Interview Date'
        ])
        for drive in drives:
            for a in drive.applications:
                writer.writerow([
                    drive.title, a.student.name, a.student.roll_no,
                    a.student.branch or '', a.student.cgpa or '',
                    a.status, a.applied_on.strftime('%Y-%m-%d'),
                    a.interview_date.strftime('%Y-%m-%d') if a.interview_date else ''
                ])

    html = render_template('email/company_export_ready.html',
        company_name=company.name, filename=filename
    )
    _send_notification(company.user.email, 'CSV Export Ready', html, is_html=True)

    return filename
