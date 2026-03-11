
 #Entry point for the Flask application.

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

#  creates and configures the Flask application

def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(config.BASE_DIR, 'frontend', 'templates'),
        static_folder=os.path.join(config.BASE_DIR, 'frontend', 'static')
    )

    # Basic config 
    app.secret_key = config.SECRET_KEY
    app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
    app.config['CACHE_DEFAULT_TIMEOUT'] = config.CACHE_DEFAULT_TIMEOUT

    # Email (SMTP) config
    app.config['MAIL_SERVER'] = config.MAIL_SERVER
    app.config['MAIL_PORT'] = config.MAIL_PORT
    app.config['MAIL_USE_TLS'] = config.MAIL_USE_TLS
    app.config['MAIL_USERNAME'] = config.MAIL_USERNAME
    app.config['MAIL_PASSWORD'] = config.MAIL_PASSWORD
    app.config['MAIL_DEFAULT_SENDER'] = config.MAIL_DEFAULT_SENDER

    # Flask-Security config
    app.config['SECURITY_PASSWORD_SALT'] = config.SECURITY_PASSWORD_SALT
    app.config['SECURITY_REGISTERABLE'] = config.SECURITY_REGISTERABLE
    app.config['SECURITY_SEND_REGISTER_EMAIL'] = config.SECURITY_SEND_REGISTER_EMAIL
    app.config['WTF_CSRF_ENABLED'] = config.WTF_CSRF_ENABLED

    #  Cache config 
    try:
        import redis as _redis
        _r = _redis.Redis.from_url(config.CACHE_REDIS_URL, socket_connect_timeout=5)
        _r.ping()
        app.config['CACHE_TYPE'] = 'RedisCache'
        app.config['CACHE_REDIS_URL'] = config.CACHE_REDIS_URL
    except Exception as _redis_err:
        print(f'[INFO] Redis not available — using SimpleCache instead ({_redis_err})')
        app.config['CACHE_TYPE'] = 'SimpleCache'

    # Initialize Flask extensions 
    db.init_app(app)
    cache.init_app(app)
    mail.init_app(app)

    # Flask-Security setup
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

    # Serve frontend JS/CSS component files
    @app.route('/frontend/<path:filename>')
    def serve_frontend(filename):
        return send_from_directory(
            os.path.join(config.BASE_DIR, 'frontend'), filename
        )

    from backend.routes.auth import auth_bp
    from backend.routes.admin import admin_bp
    from backend.routes.company import company_bp
    from backend.routes.student import student_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(company_bp)
    app.register_blueprint(student_bp)

    #  Create database tables 
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

        

    # Import celery tasks so they get registered
    import backend.tasks  # noqa: F401

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
