"""
Database models for the Placement Portal.

Models:
  Role            — Flask-Security role (admin / student / company)
  User            — Login account with role-based access
  Student         — Student profile linked to a User
  Company         — Company profile linked to a User
  PlacementDrive  — Job opening posted by a company
  Application     — A student's application to a drive
  Placement       — Final placement record after selection
"""

import uuid
from datetime import datetime
from flask_security import UserMixin, RoleMixin
from backend.extensions import db


# ------------------------------------------------------------------
#  Role — Flask-Security role-based access control
# ------------------------------------------------------------------

roles_users = db.Table('roles_users',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'))
)


class Role(db.Model, RoleMixin):
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))


# ------------------------------------------------------------------
#  User — handles authentication for all roles
# ------------------------------------------------------------------

class User(db.Model, UserMixin):
    id             = db.Column(db.Integer, primary_key=True)
    email          = db.Column(db.String(120), unique=True, nullable=False)
    password       = db.Column(db.String(255), nullable=False)
    active         = db.Column(db.Boolean, default=True)
    fs_uniquifier  = db.Column(db.String(64), unique=True, nullable=False, default=lambda: uuid.uuid4().hex)
    role           = db.Column(db.String(20), nullable=False)       # 'admin', 'student', 'company'
    is_blacklisted = db.Column(db.Boolean, default=False)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    # Flask-Security roles relationship
    roles = db.relationship('Role', secondary=roles_users, backref=db.backref('users', lazy='dynamic'))

    # One-to-one links
    student = db.relationship('Student', backref='user', uselist=False)
    company = db.relationship('Company', backref='user', uselist=False)


# ------------------------------------------------------------------
#  Student — profile, resume, skills
# ------------------------------------------------------------------

class Student(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    user_id  = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name     = db.Column(db.String(100), nullable=False)
    roll_no  = db.Column(db.String(50), unique=True, nullable=False)
    branch   = db.Column(db.String(100))
    year     = db.Column(db.Integer)
    cgpa     = db.Column(db.Float)
    phone    = db.Column(db.String(15))
    skills   = db.Column(db.Text)
    resume   = db.Column(db.String(200))
    about    = db.Column(db.Text)
    experience = db.Column(db.Text)

    applications = db.relationship('Application', backref='student', lazy=True)


# ------------------------------------------------------------------
#  Company — profile, HR contact, approval status
# ------------------------------------------------------------------

class Company(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name        = db.Column(db.String(200), nullable=False)
    industry    = db.Column(db.String(100))
    hr_name     = db.Column(db.String(100))
    hr_email    = db.Column(db.String(120))
    hr_phone    = db.Column(db.String(15))
    website     = db.Column(db.String(200))
    description = db.Column(db.Text)
    status      = db.Column(db.String(20), default='pending')      # pending / approved / rejected

    drives = db.relationship('PlacementDrive', backref='company', lazy=True)


# ------------------------------------------------------------------
#  PlacementDrive — job openings posted by companies
# ------------------------------------------------------------------

class PlacementDrive(db.Model):
    id                = db.Column(db.Integer, primary_key=True)
    company_id        = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    title             = db.Column(db.String(200), nullable=False)
    description       = db.Column(db.Text)
    eligibility       = db.Column(db.Text)                         # general eligibility text
    eligible_branches = db.Column(db.String(300))                  # comma-separated: "CSE, ECE, ME"
    min_cgpa          = db.Column(db.Float, default=0)
    eligible_year     = db.Column(db.Integer)
    skills_required   = db.Column(db.Text)
    salary            = db.Column(db.String(100))
    location          = db.Column(db.String(100))
    deadline          = db.Column(db.Date)
    status            = db.Column(db.String(20), default='pending')  # pending / approved / rejected / closed
    created_at        = db.Column(db.DateTime, default=datetime.utcnow)

    applications = db.relationship('Application', backref='drive', lazy=True)


# ------------------------------------------------------------------
#  Application — a student's application to a drive
# ------------------------------------------------------------------

class Application(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    student_id     = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    drive_id       = db.Column(db.Integer, db.ForeignKey('placement_drive.id'), nullable=False)
    applied_on     = db.Column(db.DateTime, default=datetime.utcnow)
    status         = db.Column(db.String(20), default='applied')   # applied / shortlisted / interview / selected / rejected / placed
    interview_date = db.Column(db.DateTime, nullable=True)
    notes          = db.Column(db.Text)                            # feedback / notes from company

    # Each student can apply to a drive only once
    __table_args__ = (db.UniqueConstraint('student_id', 'drive_id'),)


# ------------------------------------------------------------------
#  Placement — final placement record
# ------------------------------------------------------------------

class Placement(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    student_id     = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    company_id     = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    application_id = db.Column(db.Integer, db.ForeignKey('application.id'), nullable=False)
    position       = db.Column(db.String(200))
    salary         = db.Column(db.String(100))
    joining_date   = db.Column(db.Date)
    offer_letter   = db.Column(db.String(200))
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    student     = db.relationship('Student', backref='placements')
    company     = db.relationship('Company', backref='placements')
    application = db.relationship('Application', backref='placement', uselist=False)
