from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
from flask_mail import Mail
from celery import Celery
from celery.schedules import crontab


db = SQLAlchemy()

cache = Cache()

mail = Mail()

# Celery (background tasks)
celery = Celery(
    'backend.tasks',
    broker='redis://default:a6k9KNHl0wVrvfvy08BFeueVjWs2gKDG@redis-17393.crce276.ap-south-1-3.ec2.cloud.redislabs.com:17393/0',
    backend='redis://default:a6k9KNHl0wVrvfvy08BFeueVjWs2gKDG@redis-17393.crce276.ap-south-1-3.ec2.cloud.redislabs.com:17393/0'
)
celery.conf.broker_transport_options = {
    'socket_connect_timeout': 5,
    'socket_timeout': 5
}
celery.conf.broker_pool_limit = 1
celery.conf.result_backend_transport_options = {'max_connections': 2}
celery.conf.timezone = 'Asia/Kolkata'
celery.conf.include = ['backend.tasks']

# Scheduled tasks (Celery Beat)
celery.conf.beat_schedule = {
    'daily-reminder': {
        'task': 'backend.tasks.send_daily_reminders',
        'schedule': crontab(hour=9, minute=0),   # Every day at 9 AM
    },
    'monthly-report': {
        'task': 'backend.tasks.send_monthly_report',
        'schedule': crontab(day_of_month=1, hour=8, minute=0),  # 1st of every month at 8 AM
    },
}
