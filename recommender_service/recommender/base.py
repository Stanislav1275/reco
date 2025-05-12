from typing import List, Dict, Any, Optional
import pandas as pd
from rectools import Columns
from rectools.models import LightFMWrapperModel
from rectools.dataset import Dataset
import numpy as np

class BaseRecommender:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model = None
        self.dataset = None
        
    def prepare_dataset(self, interactions: pd.DataFrame, 
                       user_features: Optional[pd.DataFrame] = None,
                       item_features: Optional[pd.DataFrame] = None) -> Dataset:
        """
        Подготовка датасета для обучения модели
        """
        self.dataset = Dataset.construct(
            interactions_df=interactions,
            user_features_df=user_features,
            item_features_df=item_features
        )
        return self.dataset
    
    def train(self, dataset: Optional[Dataset] = None) -> None:
        """
        Обучение модели
        """
        if dataset is not None:
            self.dataset = dataset
            
        if self.dataset is None:
            raise ValueError("Dataset is not prepared")
            
        self.model = LightFMWrapperModel(**self.config['model_params'])
        self.model.fit(self.dataset)
        
    def get_user_recommendations(self, user_id: int, k: int = 40) -> List[Dict[str, Any]]:
        """
        Получение рекомендаций для пользователя
        """
        if self.model is None:
            raise ValueError("Model is not trained")
            
        recommendations = self.model.recommend(
            users=[user_id],
            dataset=self.dataset,
            k=k,
            filter_viewed=True
        )
        
        return self._format_recommendations(recommendations)
    
    def get_similar_items(self, item_id: int, k: int = 20) -> List[Dict[str, Any]]:
        """
        Получение похожих произведений
        """
        if self.model is None:
            raise ValueError("Model is not trained")
            
        # Получаем эмбеддинги для всех предметов
        item_embeddings = self.model.get_item_embeddings()
        
        # Находим индекс нужного предмета
        item_idx = self.dataset.item_id_map.to_internal(item_id)
        
        # Вычисляем косинусное сходство
        similarities = np.dot(item_embeddings, item_embeddings[item_idx])
        
        # Получаем топ-k похожих предметов
        similar_indices = np.argsort(similarities)[::-1][1:k+1]
        similar_items = self.dataset.item_id_map.to_external(similar_indices)
        
        return self._format_similar_items(similar_items, similarities[similar_indices])
    
    def _format_recommendations(self, recommendations: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Форматирование рекомендаций
        """
        return [
            {
                'id': row[Columns.Item],
                'score': float(row[Columns.Score])
            }
            for _, row in recommendations.iterrows()
        ]
    
    def _format_similar_items(self, items: np.ndarray, scores: np.ndarray) -> List[Dict[str, Any]]:
        """
        Форматирование похожих предметов
        """
        return [
            {
                'id': int(item_id),
                'score': float(score)
            }
            for item_id, score in zip(items, scores)
        ] 