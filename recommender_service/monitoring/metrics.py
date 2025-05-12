from prometheus_client import Counter, Histogram, Gauge, Summary
from functools import wraps
import time

# Метрики для рекомендаций
RECOMMENDATION_REQUESTS = Counter(
    'recommendation_requests_total',
    'Общее количество запросов рекомендаций',
    ['type']  # user_recommendations или similar_titles
)

RECOMMENDATION_LATENCY = Histogram(
    'recommendation_latency_seconds',
    'Время выполнения запросов рекомендаций',
    ['type'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0)
)

RECOMMENDATION_CACHE_HITS = Counter(
    'recommendation_cache_hits_total',
    'Количество попаданий в кеш рекомендаций',
    ['type']
)

RECOMMENDATION_CACHE_MISSES = Counter(
    'recommendation_cache_misses_total',
    'Количество промахов кеша рекомендаций',
    ['type']
)

# Метрики для обучения модели
MODEL_TRAINING_DURATION = Histogram(
    'model_training_duration_seconds',
    'Время обучения модели',
    buckets=(300, 600, 1800, 3600, 7200)
)

MODEL_TRAINING_SUCCESS = Counter(
    'model_training_success_total',
    'Количество успешных обучений модели'
)

MODEL_TRAINING_FAILURES = Counter(
    'model_training_failures_total',
    'Количество неудачных обучений модели'
)

# Метрики для метрик модели
MODEL_METRICS = Gauge(
    'model_metrics',
    'Значения метрик модели',
    ['metric_name']
)

# Метрики для сбора данных
DATA_PREPARATION_DURATION = Histogram(
    'data_preparation_duration_seconds',
    'Время подготовки данных',
    ['stage'],  # interactions, user_features, item_features
    buckets=(1, 5, 10, 30, 60, 300)
)

DATA_PREPARATION_ERRORS = Counter(
    'data_preparation_errors_total',
    'Количество ошибок при подготовке данных',
    ['stage']
)

# Метрики для кеша
CACHE_SIZE = Gauge(
    'cache_size_bytes',
    'Размер кеша в байтах'
)

CACHE_ITEMS = Gauge(
    'cache_items_total',
    'Количество элементов в кеше'
)

def track_time(metric: Histogram, labels: dict = None):
    """
    Декоратор для отслеживания времени выполнения функции
    
    Args:
        metric: Метрика Histogram для записи времени
        labels: Метки для метрики
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)
        return wrapper
    return decorator

def track_errors(metric: Counter, labels: dict = None):
    """
    Декоратор для отслеживания ошибок
    
    Args:
        metric: Метрика Counter для подсчета ошибок
        labels: Метки для метрики
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if labels:
                    metric.labels(**labels).inc()
                else:
                    metric.inc()
                raise
        return wrapper
    return decorator 