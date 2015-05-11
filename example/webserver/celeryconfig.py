from datetime import timedelta
from celery.schedules import crontab

BROKER_URL = 'amqp://guest@localhost//'
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT=['json']
CELERY_TIMEZONE = 'US/Eastern'
#CELERYBEAT_SCHEDULE = {
 #   'add-every-30-seconds': {
  #      'task': 'tasks.add',
   #     'schedule':  timedelta(seconds=2),
    #    'args': (16, 16),
     #   'options': {'expires': 10},
 #   },
#}