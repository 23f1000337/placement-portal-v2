"""
Celery worker entry point.
Run:  celery -A backend.celery_worker.celery worker --loglevel=info --pool=solo
This ensures the Flask app is created (setting up ContextTask) before tasks run.
"""

from backend.app import create_app
from backend.extensions import celery

app = create_app()

# Import tasks so they are registered
import backend.tasks  # noqa: F401
