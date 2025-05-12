from typing import Dict, Any
import logging
from datetime import datetime, timedelta
import os
from celery import Task
from internal.database import get_db
from internal.models.models import Config, TrainingHistory, ModelArtifact
from recommender.base import BaseRecommender
from recommender_service.internal.service.data_preparation import DataPreparationService
from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

class TrainingTask(Task):
    """Базовый класс для задач обучения с обработкой ошибок"""
    _abstract = True
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Обработка ошибок при выполнении задачи"""
        logger.error(f"Ошибка при выполнении задачи {task_id}: {exc}")
        with get_db() as db:
            training = db.query(TrainingHistory).filter_by(task_id=task_id).first()
            if training:
                training.status = "failed"
                training.error_message = str(exc)
                db.commit()

@celery_app.task(bind=True, base=TrainingTask, queue='training')
async def train_model(self, config_id: int) -> Dict[str, Any]:
    """
    Задача для обучения модели рекомендаций
    
    Args:
        config_id: ID конфигурации для обучения
        
    Returns:
        Словарь с результатами обучения
    """
    logger.info(f"Начало обучения модели с конфигурацией {config_id}")
    
    with get_db() as db:
        # Получаем конфигурацию
        config = db.query(Config).get(config_id)
        if not config:
            raise ValueError(f"Конфигурация {config_id} не найдена")
            
        # Создаем запись в истории обучения
        training = TrainingHistory(
            config_id=config_id,
            task_id=self.request.id,
            status="running",
            training_params=config.model_params
        )
        db.add(training)
        db.commit()
        
        try:
            # Подготавливаем данные
            interactions = await DataPreparationService.get_interactions()
            user_features = await DataPreparationService.get_users_features()
            item_features = await DataPreparationService.get_titles_features()
            
            # Создаем и обучаем модель
            recommender = BaseRecommender(config.model_params)
            recommender.prepare_dataset(interactions, user_features, item_features)
            recommender.train()
            
            # Сохраняем артефакты модели
            artifact = ModelArtifact(
                config_id=config_id,
                training_id=training.id,
                artifact_path=f"models/model_{training.id}.pkl",
                artifact_type="model",
                is_active=True
            )
            db.add(artifact)
            
            # Обновляем статус обучения
            training.status = "completed"
            training.completed_at = datetime.utcnow()
            
            db.commit()
            
            return {
                "status": "success",
                "training_id": training.id,
                "artifact_id": artifact.id
            }
            
        except Exception as e:
            logger.error(f"Ошибка при обучении модели: {e}")
            training.status = "failed"
            training.error_message = str(e)
            db.commit()
            raise

@celery_app.task(queue='training')
def cleanup_old_models(days: int = 30) -> Dict[str, Any]:
    """
    Задача для очистки старых моделей
    
    Args:
        days: Количество дней, после которых модель считается устаревшей
        
    Returns:
        Словарь с результатами очистки
    """
    logger.info(f"Начало очистки моделей старше {days} дней")
    
    with get_db() as db:
        # Получаем старые неактивные артефакты
        old_artifacts = db.query(ModelArtifact).filter(
            ModelArtifact.is_active == False,
            ModelArtifact.created_at < datetime.utcnow() - timedelta(days=days)
        ).all()
        
        # Удаляем файлы моделей
        for artifact in old_artifacts:
            try:
                if os.path.exists(artifact.artifact_path):
                    os.remove(artifact.artifact_path)
                db.delete(artifact)
            except Exception as e:
                logger.error(f"Ошибка при удалении артефакта {artifact.id}: {e}")
        
        db.commit()
        
        return {
            "status": "success",
            "deleted_artifacts": len(old_artifacts)
        } 