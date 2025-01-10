import os
from pathlib import Path

from celery import Celery
import environ

env = environ.Env(RABBITMQ_BROKER_URL=(str, 'amqp://flowback:flowback@localhost:5672/flowback'))
BASE_DIR = Path(__file__).resolve().parent.parent
env.read_env(os.path.join(BASE_DIR, ".env"))

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

app = Celery('backend')
broker_url = env('RABBITMQ_BROKER_URL')
beat_scheduler = "django_celery_beat.schedulers:DatabaseScheduler"

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')