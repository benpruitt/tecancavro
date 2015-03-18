from celery import Celery
from datetime import timedelta
from celery.schedules import crontab
from celery.task import periodic_task

app = Celery('tasks', backend='amqp', broker='amqp://guest@localhost//')
app.config_from_object('celeryconfig')

@app.task
def add(x, y):
    return x + y

add.apply_async((2, 2), countdown=10)
