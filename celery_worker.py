from celery import Celery
from config import Config
import time

def make_celery():
    """
    Create and configure the Celery instance.
    Works in both local and production modes.
    """
    celery = Celery(
        "talktotext",
        broker=Config.REDIS_URL,
        backend=Config.REDIS_URL,
        include=["core.tasks"],
    )

    # Celery configuration
    celery.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        broker_connection_retry_on_startup=True,
    )

    return celery


# Initialize Celery
celery = make_celery()


@celery.task(name="health.check")
def health_check():
    """
    Simple test task to confirm Celery <-> Redis <-> Worker connectivity.
    """
    return {"status": "ok", "env": Config.APP_ENV}
