"""
Celery Configuration
Background task processing for SMS reminders and payment verification.
"""

from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "sha_reminder",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Task routing
celery_app.conf.task_routes = {
    "tasks.reminder_tasks.*": {"queue": "reminders"},
    "tasks.payment_tasks.*": {"queue": "payments"},
}

# Scheduled tasks (Celery Beat)
celery_app.conf.beat_schedule = {
    # Daily: Check for payment due reminders (send on day 5 of each month)
    "send-payment-reminders": {
        "task": "tasks.reminder_tasks.check_and_send_reminders",
        "schedule": crontab(hour=8, minute=0, day_of_month="1,5,8"),
        "options": {"queue": "reminders"},
    },
    # Daily: Check for overdue payments (send on day 10 of each month)
    "send-overdue-reminders": {
        "task": "tasks.reminder_tasks.check_overdue_payments",
        "schedule": crontab(hour=10, minute=0, day_of_month="10,15,20,25"),
        "options": {"queue": "reminders"},
    },
}

# Serialization
celery_app.conf.accept_content = ["json"]
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.timezone = "Africa/Nairobi"


@celery_app.task(bind=True, max_retries=3)
def debug_task(self):
    """Debug task to verify Celery is working."""
    print(f"Request: {self.request!r}")
    return "Celery is running"