import os

# Project root directory (parent of backend/)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

SECRET_KEY = 'placement-portal-secret-key-2026'

# Flask-Security
SECURITY_PASSWORD_SALT = os.environ.get('SECURITY_PASSWORD_SALT', 'placement-salt-2026')
SECURITY_REGISTERABLE = False
SECURITY_SEND_REGISTER_EMAIL = False
WTF_CSRF_ENABLED = False


SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'placement.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

# Caching (Redis preferred, SimpleCache as fallback)
CACHE_TYPE = 'RedisCache'
CACHE_REDIS_URL = 'redis://default:a6k9KNHl0wVrvfvy08BFeueVjWs2gKDG@redis-17393.crce276.ap-south-1-3.ec2.cloud.redislabs.com:17393/0'
CACHE_DEFAULT_TIMEOUT = 120

MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@placement.portal')
MAIL_TIMEOUT = 5

