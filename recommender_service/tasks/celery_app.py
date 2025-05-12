from celery import Celery
from config.settings import settings

# Создаем экземпляр Celery
celery_app = Celery(
    'recommender',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=['tasks.training', 'tasks.metrics']
)

# Конфигурация Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 час
    worker_max_tasks_per_child=1000,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_queue='recommender',
    task_queues={
        'recommender': {
            'exchange': 'recommender',
            'routing_key': 'recommender',
        },
        'training': {
            'exchange': 'training',
            'routing_key': 'training',
        },
        'metrics': {
            'exchange': 'metrics',
            'routing_key': 'metrics',
        }
    }
)

if __name__ == '__main__':
    celery_app.start() 