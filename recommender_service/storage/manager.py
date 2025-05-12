import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import pickle
import shutil

from config.settings import settings
from internal.database import get_db
from internal.models.models import ModelArtifact, Config

logger = logging.getLogger(__name__)

class StorageManager:
    """Менеджер для хранения данных и моделей"""
    
    def __init__(self):
        """Инициализация менеджера хранилища"""
        self.data_dir = settings.DATA_DIR
        self.models_dir = settings.MODELS_DIR
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Создание необходимых директорий"""
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.models_dir, exist_ok=True)
    
    def save_dataset(self, 
                    interactions: Dict[str, Any],
                    user_features: Optional[Dict[str, Any]] = None,
                    item_features: Optional[Dict[str, Any]] = None,
                    metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Сохранение датасета
        
        Args:
            interactions: Словарь с взаимодействиями
            user_features: Признаки пользователей
            item_features: Признаки произведений
            metadata: Метаданные датасета
            
        Returns:
            Путь к сохраненному датасету
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dataset_dir = os.path.join(self.data_dir, f"dataset_{timestamp}")
        os.makedirs(dataset_dir, exist_ok=True)
        
        # Сохранение данных
        with open(os.path.join(dataset_dir, "interactions.pkl"), "wb") as f:
            pickle.dump(interactions, f)
            
        if user_features:
            with open(os.path.join(dataset_dir, "user_features.pkl"), "wb") as f:
                pickle.dump(user_features, f)
                
        if item_features:
            with open(os.path.join(dataset_dir, "item_features.pkl"), "wb") as f:
                pickle.dump(item_features, f)
        
        # Сохранение метаданных
        metadata = metadata or {}
        metadata.update({
            "timestamp": timestamp,
            "interactions_count": len(interactions),
            "user_features_count": len(user_features) if user_features else 0,
            "item_features_count": len(item_features) if item_features else 0
        })
        
        with open(os.path.join(dataset_dir, "metadata.json"), "w") as f:
            json.dump(metadata, f, indent=2)
            
        logger.info(f"Датасет сохранен в {dataset_dir}")
        return dataset_dir
    
    def load_dataset(self, dataset_dir: str) -> Dict[str, Any]:
        """
        Загрузка датасета
        
        Args:
            dataset_dir: Путь к директории с датасетом
            
        Returns:
            Словарь с данными датасета
        """
        dataset = {}
        
        # Загрузка взаимодействий
        interactions_path = os.path.join(dataset_dir, "interactions.pkl")
        if os.path.exists(interactions_path):
            with open(interactions_path, "rb") as f:
                dataset["interactions"] = pickle.load(f)
        
        # Загрузка признаков пользователей
        user_features_path = os.path.join(dataset_dir, "user_features.pkl")
        if os.path.exists(user_features_path):
            with open(user_features_path, "rb") as f:
                dataset["user_features"] = pickle.load(f)
        
        # Загрузка признаков произведений
        item_features_path = os.path.join(dataset_dir, "item_features.pkl")
        if os.path.exists(item_features_path):
            with open(item_features_path, "rb") as f:
                dataset["item_features"] = pickle.load(f)
        
        # Загрузка метаданных
        metadata_path = os.path.join(dataset_dir, "metadata.json")
        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                dataset["metadata"] = json.load(f)
        
        return dataset
    
    def save_model(self, 
                  model: Any,
                  config_id: int,
                  metrics: Dict[str, float],
                  is_active: bool = False) -> str:
        """
        Сохранение модели
        
        Args:
            model: Объект модели
            config_id: ID конфигурации
            metrics: Метрики модели
            is_active: Флаг активной модели
            
        Returns:
            Путь к сохраненной модели
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_dir = os.path.join(self.models_dir, f"model_{timestamp}")
        os.makedirs(model_dir, exist_ok=True)
        
        # Сохранение модели
        model_path = os.path.join(model_dir, "model.pkl")
        with open(model_path, "wb") as f:
            pickle.dump(model, f)
        
        # Сохранение метрик
        metrics_path = os.path.join(model_dir, "metrics.json")
        with open(metrics_path, "w") as f:
            json.dump(metrics, f, indent=2)
        
        # Сохранение в БД
        with get_db() as db:
            artifact = ModelArtifact(
                config_id=config_id,
                artifact_path=model_dir,
                metrics=metrics,
                is_active=is_active,
                created_at=datetime.now()
            )
            db.add(artifact)
            db.commit()
            
            if is_active:
                # Деактивация других моделей
                db.query(ModelArtifact).filter(
                    ModelArtifact.config_id == config_id,
                    ModelArtifact.id != artifact.id
                ).update({"is_active": False})
                db.commit()
        
        logger.info(f"Модель сохранена в {model_dir}")
        return model_dir
    
    def load_model(self, model_dir: str) -> Any:
        """
        Загрузка модели
        
        Args:
            model_dir: Путь к директории с моделью
            
        Returns:
            Загруженная модель
        """
        model_path = os.path.join(model_dir, "model.pkl")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Модель не найдена: {model_path}")
            
        with open(model_path, "rb") as f:
            model = pickle.load(f)
            
        return model
    
    def get_active_model_path(self, config_id: int) -> Optional[str]:
        """
        Получение пути к активной модели
        
        Args:
            config_id: ID конфигурации
            
        Returns:
            Путь к активной модели или None
        """
        with get_db() as db:
            artifact = db.query(ModelArtifact).filter_by(
                config_id=config_id,
                is_active=True
            ).first()
            
            return artifact.artifact_path if artifact else None
    
    def cleanup_old_models(self, days: int = 30):
        """
        Удаление старых моделей
        
        Args:
            days: Возраст моделей в днях для удаления
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with get_db() as db:
            old_artifacts = db.query(ModelArtifact).filter(
                ModelArtifact.created_at < cutoff_date,
                ModelArtifact.is_active == False
            ).all()
            
            for artifact in old_artifacts:
                try:
                    if os.path.exists(artifact.artifact_path):
                        shutil.rmtree(artifact.artifact_path)
                    db.delete(artifact)
                except Exception as e:
                    logger.error(f"Ошибка при удалении модели {artifact.artifact_path}: {e}")
            
            db.commit() 