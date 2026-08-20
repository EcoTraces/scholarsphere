from app.services.notification_dispatch import (
    process_due_notifications_task,
    retry_failed_notifications_task,
)
from app.tasks.opportunity_sync import celery_app, run_async_safely


@celery_app.task(name="app.tasks.notifications.process_due_notifications")
def process_due_notifications() -> dict[str, int]:
    return run_async_safely(process_due_notifications_task())


@celery_app.task(name="app.tasks.notifications.retry_failed_notifications")
def retry_failed_notifications() -> dict[str, int]:
    return run_async_safely(retry_failed_notifications_task())
