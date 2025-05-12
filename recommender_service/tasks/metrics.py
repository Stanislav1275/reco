from typing import Dict, Any, List
import logging
from datetime import datetime, timedelta
from celery import Task
from internal.database import get_db
from internal.models.models import Config, Metrics, TrainingHistory
from recommender.base import BaseRecommender
from recommender_service.internal.service.data_preparation import DataPreparationService
from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

class MetricsTask(Task):
    """Базовый класс для задач сбора метрик с обработкой ошибок"""
    _abstract = True
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Обработка ошибок при выполнении задачи"""
        logger.error(f"Ошибка при сборе метрик {task_id}: {exc}")

@celery_app.task(bind=True, base=MetricsTask, queue='metrics')
async def collect_metrics(self, config_id: int, training_id: int) -> Dict[str, Any]:
    """
    Задача для сбора метрик производительности модели
    
    Args:
        config_id: ID конфигурации
        training_id: ID обучения
        
    Returns:
        Словарь с результатами сбора метрик
    """
    logger.info(f"Начало сбора метрик для обучения {training_id}")
    
    with get_db() as db:
        # Получаем конфигурацию и историю обучения
        config = db.query(Config).get(config_id)
        training = db.query(TrainingHistory).get(training_id)
        
        if not config or not training:
            raise ValueError("Конфигурация или история обучения не найдены")
            
        try:
            # Подготавливаем данные для валидации
            interactions = await DataPreparationService.get_interactions()
            user_features = await DataPreparationService.get_users_features()
            item_features = await DataPreparationService.get_titles_features()
            
            # Создаем и обучаем модель
            recommender = BaseRecommender(config.model_params)
            recommender.prepare_dataset(interactions, user_features, item_features)
            
            # Собираем метрики
            metrics = []
            for metric_name in config.metrics:
                try:
                    metric_value = recommender.evaluate_metric(metric_name)
                    metrics.append(Metrics(
                        config_id=config_id,
                        training_id=training_id,
                        metric_name=metric_name,
                        metric_value=metric_value,
                        timestamp=datetime.utcnow()
                    ))
                except Exception as e:
                    logger.error(f"Ошибка при сборе метрики {metric_name}: {e}")
            
            # Сохраняем метрики
            db.add_all(metrics)
            db.commit()
            
            return {
                "status": "success",
                "metrics_collected": len(metrics)
            }
            
        except Exception as e:
            logger.error(f"Ошибка при сборе метрик: {e}")
            raise

@celery_app.task(queue='metrics')
def cleanup_old_metrics(days: int = 90) -> Dict[str, Any]:
    """
    Задача для очистки старых метрик
    
    Args:
        days: Количество дней, после которых метрики считаются устаревшими
        
    Returns:
        Словарь с результатами очистки
    """
    logger.info(f"Начало очистки метрик старше {days} дней")
    
    with get_db() as db:
        # Получаем старые метрики
        old_metrics = db.query(Metrics).filter(
            Metrics.timestamp < datetime.utcnow() - timedelta(days=days)
        ).all()
        
        # Удаляем метрики
        for metric in old_metrics:
            db.delete(metric)
        
        db.commit()
        
        return {
            "status": "success",
            "deleted_metrics": len(old_metrics)
        } 