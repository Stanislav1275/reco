import logging
import uuid
import asyncio
import pickle
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

import pandas as pd
from rectools import Columns
from rectools.dataset import Dataset
from rectools.models import PopularModel
from rectools.metrics import Precision, Recall, MAP, NDCG, calc_metrics, MeanInvUserFreq, Serendipity

from recommender_service.config.internal.models import (
    ModelConfig, ModelMetrics, TrainingHistory, ModelCheckpoint
)
from recommender_service.internal.data.internal_adapter import MongoDBAdapter
from recommender_service.internal.data.redis_adapter import RedisAdapter

logger = logging.getLogger(__name__)

class RecommenderService:
    """Сервис для работы с рекомендациями"""
    
    def __init__(
        self,
        mongodb_adapter: MongoDBAdapter,
        redis_adapter: RedisAdapter,
        dataset_dir: str = "data/datasets"
    ):
        self._mongodb_adapter = mongodb_adapter
        self._redis_adapter = redis_adapter
        self._dataset_dir = Path(dataset_dir)
        self._ensure_dataset_dir()
        
    def _ensure_dataset_dir(self) -> None:
        """Создает директорию для датасетов, если она не существует."""
        try:
            self._dataset_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Ошибка при создании директории датасетов: {e}")
            raise

    def _get_dataset_path(self, config_id: str) -> Path:
        """Возвращает путь к файлу датасета для конфигурации."""
        return self._dataset_dir / f"{config_id}.pkl"
        
    def _save_dataset(self, config_id: str, dataset: Dataset) -> None:
        """Сохраняет датасет в файл."""
        try:
            dataset_path = self._get_dataset_path(config_id)
            with open(dataset_path, 'wb') as f:
                pickle.dump(dataset, f)
            logger.info(f"Датасет сохранен в {dataset_path}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении датасета: {e}")
            raise
            
    def _load_dataset(self, config_id: str) -> Optional[Dataset]:
        """Загружает датасет из файла."""
        try:
            dataset_path = self._get_dataset_path(config_id)
            if not dataset_path.exists():
                return None
            with open(dataset_path, 'rb') as f:
                dataset = pickle.load(f)
            logger.info(f"Датасет загружен из {dataset_path}")
            return dataset
        except Exception as e:
            logger.error(f"Ошибка при загрузке датасета: {e}")
            return None
            
    def _cleanup_old_datasets(self, keep_config_ids: List[str]) -> None:
        """Удаляет старые датасеты, оставляя только указанные конфигурации."""
        try:
            for dataset_file in self._dataset_dir.glob("*.pkl"):
                config_id = dataset_file.stem
                if config_id not in keep_config_ids:
                    dataset_file.unlink()
                    logger.info(f"Удален старый датасет: {dataset_file}")
        except Exception as e:
            logger.error(f"Ошибка при очистке старых датасетов: {e}")
            
    async def get_recommendations(
        self,
        config_id: str,
        user_id: int,
        k: int = 10,
        filter_viewed: bool = True
    ) -> List[Dict[str, Any]]:
        """Получает рекомендации для пользователя."""
        try:
            # Валидация входных данных
            if not isinstance(user_id, int) or user_id <= 0:
                raise ValueError("user_id должен быть положительным целым числом")
            if not isinstance(k, int) or k <= 0:
                raise ValueError("k должен быть положительным целым числом")

            # Получаем модель из кэша или MongoDB
            model = await self._get_model(config_id)
            if not model:
                raise ValueError(f"Модель для конфигурации {config_id} не найдена")
                
            # Загружаем или создаем датасет
            dataset = self._load_dataset(config_id)
            if not dataset:
                interactions = await self._get_interactions(config_id)
                if not interactions:
                    raise ValueError(f"Нет данных о взаимодействиях для конфигурации {config_id}")
                dataset = Dataset(interactions)
                self._save_dataset(config_id, dataset)
                
            # Получаем рекомендации
            recommendations = model.recommend(
                users=[user_id],
                dataset=dataset,
                k=k,
                filter_viewed=filter_viewed
            )
            
            # Форматируем результат
            result = []
            for _, row in recommendations.iterrows():
                result.append({
                    "item_id": int(row[Columns.Item]),
                    "score": float(row[Columns.Score]),
                    "rank": int(row[Columns.Rank])
                })
                
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при получении рекомендаций: {e}")
            raise
            
    async def train_model(self, config_id: str) -> str:
        """Обучает модель для указанной конфигурации."""
        try:
            # Получаем конфигурацию
            config = await self._mongodb_adapter.get_model_config(config_id)
            if not config:
                raise ValueError(f"Конфигурация {config_id} не найдена")
                
            # Проверяем необходимость переобучения
            if not await self._should_retrain(config):
                logger.info(f"Переобучение не требуется для конфигурации {config_id}")
                return config.active_model_version
                
            # Получаем данные о взаимодействиях
            interactions = await self._get_interactions(config_id)
            if not interactions:
                raise ValueError(f"Нет данных о взаимодействиях для конфигурации {config_id}")
                
            # Создаем и сохраняем датасет
            dataset = Dataset(interactions)
            self._save_dataset(config_id, dataset)
            
            # Обучаем модель
            model = PopularModel()
            model.fit(dataset)
            
            # Генерируем новую версию
            model_version = str(uuid.uuid4())
            
            # Сохраняем модель
            current_version = config.active_model_version
            await self._mongodb_adapter.save_model_checkpoint(
                model_name=config_id,
                version=model_version,
                checkpoint_data=model.get_params()
            )
            
            # Удаляем старые версии
            if current_version:
                await self._mongodb_adapter.delete_old_model_versions(
                    model_name=config_id,
                    keep_versions=[current_version, model_version]
                )
                
            # Очищаем старые датасеты
            self._cleanup_old_datasets([config_id])
            
            # Сохраняем историю обучения
            history = TrainingHistory(
                model_name=config_id,
                version=model_version,
                training_date=datetime.utcnow(),
                metrics=ModelMetrics(
                    precision=0.0,  # TODO: Добавить расчет метрик
                    recall=0.0,
                    novelty=0.0,
                    serendipity=0.0
                )
            )
            await self._mongodb_adapter.save_training_history(history)
            
            return model_version
            
        except Exception as e:
            logger.error(f"Ошибка при обучении модели: {e}")
            raise
            
    async def get_configs(
        self,
        site_ids: Optional[List[int]] = None,
        active: bool = True
    ) -> List[ModelConfig]:
        """Получение конфигураций моделей"""
        try:
            return await self._mongodb_adapter.get_model_configs(
                site_ids=site_ids,
                active=active
            )
        except Exception as e:
            logger.error(f"Ошибка при получении конфигураций: {str(e)}")
            raise
            
    async def get_model_metrics(
        self,
        config_id: str,
        version: Optional[str] = None
    ) -> Optional[ModelMetrics]:
        """Получение метрик модели"""
        try:
            if not version:
                config = await self._mongodb_adapter.get_model_config(config_id)
                if not config:
                    raise ValueError(f"Конфигурация {config_id} не найдена")
                version = config.active_model_version
                
            return await self._mongodb_adapter.get_model_metrics(
                model_name=config_id,
                version=version
            )
        except Exception as e:
            logger.error(f"Ошибка при получении метрик: {str(e)}")
            raise
            
    async def _get_model(self, config_id: str) -> Optional[PopularModel]:
        """Получает модель из кэша или MongoDB."""
        try:
            # Пробуем получить из кэша
            cached_model = await self._redis_adapter.get_cached_model(config_id)
            if cached_model:
                model = PopularModel()
                model.set_params(cached_model)
                return model
                
            # Получаем из MongoDB
            config = await self._mongodb_adapter.get_model_config(config_id)
            if not config or not config.active_model_version:
                return None
                
            checkpoint = await self._mongodb_adapter.get_model_checkpoint(
                config_id,
                config.active_model_version
            )
            if not checkpoint:
                return None
                
            # Создаем и кэшируем модель
            model = PopularModel()
            model.set_params(checkpoint.checkpoint_data)
            await self._redis_adapter.cache_model(
                config_id,
                config.active_model_version,
                checkpoint.checkpoint_data
            )
            
            return model
            
        except Exception as e:
            logger.error(f"Ошибка при получении модели: {e}")
            return None
            
    async def _get_interactions(self, config_id: str) -> Optional[Any]:
        """Получает матрицу взаимодействий из кэша или MongoDB."""
        try:
            # Пробуем получить из кэша
            cached_interactions = await self._redis_adapter.get_cached_interactions(config_id)
            if cached_interactions:
                return cached_interactions
                
            # Получаем из MongoDB
            interactions = await self._mongodb_adapter.get_interactions(config_id)
            if not interactions:
                return None
                
            # Кэшируем взаимодействия
            await self._redis_adapter.cache_interactions(config_id, interactions)
            
            return interactions
            
        except Exception as e:
            logger.error(f"Ошибка при получении взаимодействий: {e}")
            return None
            
    async def _should_retrain(self, config: ModelConfig) -> bool:
        """Проверяет необходимость переобучения модели."""
        try:
            if not config.active_model_version:
                return True
                
            history = await self._mongodb_adapter.get_training_history(
                config.model_name,
                config.active_model_version
            )
            if not history:
                return True
                
            # Проверяем интервал переобучения
            if config.retrain_interval:
                last_training = history.training_date
                if datetime.utcnow() - last_training > timedelta(hours=config.retrain_interval):
                    return True
                
            return False
            
        except Exception as e:
            logger.error(f"Ошибка при проверке необходимости переобучения: {e}")
            return True 