
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ticket_system.settings')

app = Celery('ticket_system')
app.config_from_object('django.conf:settings', namespace='CELERRY')
app.autodiscover_tasks()
