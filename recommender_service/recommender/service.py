import logging
from typing import List, Dict, Any
import pandas as pd
from rectools import Columns

from recommender_service.internal.data.factory import DataPreparationFactory
from recommender_service.config.settings import settings

logger = logging.getLogger(__name__)

class RecommenderService:
    def __init__(self):
        self.data_service = DataPreparationFactory.get_instance()
        self._interactions_df: Optional[pd.DataFrame] = None
        self._user_features_df: Optional[pd.DataFrame] = None
        self._title_features_df: Optional[pd.DataFrame] = None
        
    async def prepare_data(self):
        """
        Подготовка всех необходимых данных
        """
        try:
            logger.info("Начало подготовки данных для рекомендаций")
            data = await self.data_service.prepare_all()
            
            self._interactions_df = data["interactions"]
            self._user_features_df = data["user_features"]
            self._title_features_df = data["title_features"]
            
            logger.info("Данные успешно подготовлены")
        except Exception as e:
            logger.error(f"Ошибка при подготовке данных: {str(e)}")
            raise
            
    async def get_recommendations(
        self,
        user_id: int,
        n_recommendations: int = 10,
        filter_params: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Получение рекомендаций для пользователя
        
        Args:
            user_id: ID пользователя
            n_recommendations: Количество рекомендаций
            filter_params: Параметры фильтрации
            
        Returns:
            Список рекомендаций
        """
        if self._interactions_df is None:
            await self.prepare_data()
            
        # Получаем историю взаимодействий пользователя
        user_interactions = self._interactions_df[
            self._interactions_df[Columns.User] == user_id
        ]
        
        # Получаем признаки пользователя
        user_features = self._user_features_df[
            self._user_features_df["id"] == user_id
        ]
        
        # Здесь должна быть логика рекомендаций
        # Например, использование LightFM или другой модели
        
        # Временная заглушка для примера
        return [
            {
                "title_id": 1,
                "score": 0.9,
                "reason": "Похоже на ваши предыдущие выборы"
            }
        ]
        
    async def refresh_recommendations(self):
        """
        Принудительное обновление данных для рекомендаций
        """
        await self.data_service.refresh_data()
        await self.prepare_data()
        
    def __del__(self):
        """
        Очистка ресурсов при удалении сервиса
        """
        DataPreparationFactory.close() 