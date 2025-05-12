from typing import List, Dict, Any
import numpy as np
from rectools.metrics import (
    Precision, Recall, MAP, NDCG, 
    Serendipity, Diversity, Novelty
)
from sklearn.model_selection import KFold
import logging

logger = logging.getLogger(__name__)

class RecommenderMetrics:
    """Класс для оценки качества рекомендаций"""
    
    def __init__(self, k_values: List[int] = [5, 10, 20]):
        """
        Инициализация метрик
        
        Args:
            k_values: Список значений k для метрик
        """
        self.k_values = k_values
        self.metrics = {
            'precision': Precision(k=k_values),
            'recall': Recall(k=k_values),
            'map': MAP(k=k_values),
            'ndcg': NDCG(k=k_values),
            'serendipity': Serendipity(k=k_values),
            'diversity': Diversity(k=k_values),
            'novelty': Novelty(k=k_values)
        }
    
    def evaluate(self, 
                interactions: Dict[str, Any],
                recommendations: Dict[str, List[int]],
                user_features: Dict[str, Any] = None,
                item_features: Dict[str, Any] = None) -> Dict[str, float]:
        """
        Оценка качества рекомендаций
        
        Args:
            interactions: Словарь с взаимодействиями пользователей
            recommendations: Словарь с рекомендациями для пользователей
            user_features: Признаки пользователей (опционально)
            item_features: Признаки произведений (опционально)
            
        Returns:
            Словарь с метриками
        """
        results = {}
        
        for metric_name, metric in self.metrics.items():
            try:
                score = metric.calc(interactions, recommendations)
                results[metric_name] = score
                logger.info(f"Метрика {metric_name}: {score:.4f}")
            except Exception as e:
                logger.error(f"Ошибка при расчете метрики {metric_name}: {e}")
                results[metric_name] = None
                
        return results

def cross_validate(model_class, 
                  interactions: Dict[str, Any],
                  n_splits: int = 5,
                  **model_params) -> Dict[str, List[float]]:
    """
    Кросс-валидация модели рекомендаций
    
    Args:
        model_class: Класс модели рекомендаций
        interactions: Словарь с взаимодействиями
        n_splits: Количество фолдов
        **model_params: Параметры модели
        
    Returns:
        Словарь с результатами метрик по фолдам
    """
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)
    user_ids = list(interactions.keys())
    
    results = {
        'precision': [], 'recall': [], 'map': [], 
        'ndcg': [], 'serendipity': [], 'diversity': [], 'novelty': []
    }
    
    for fold, (train_idx, val_idx) in enumerate(kf.split(user_ids)):
        logger.info(f"Фолд {fold + 1}/{n_splits}")
        
        # Разделение на train/val
        train_users = [user_ids[i] for i in train_idx]
        val_users = [user_ids[i] for i in val_idx]
        
        train_interactions = {
            uid: interactions[uid] for uid in train_users
        }
        val_interactions = {
            uid: interactions[uid] for uid in val_users
        }
        
        # Обучение модели
        model = model_class(**model_params)
        model.fit(train_interactions)
        
        # Получение рекомендаций
        recommendations = {
            uid: model.recommend(uid, k=20) 
            for uid in val_users
        }
        
        # Оценка качества
        metrics = RecommenderMetrics()
        fold_results = metrics.evaluate(
            val_interactions, 
            recommendations
        )
        
        # Сохранение результатов
        for metric_name, value in fold_results.items():
            if value is not None:
                results[metric_name].append(value)
    
    # Расчет средних значений
    for metric_name in results:
        if results[metric_name]:
            mean_value = np.mean(results[metric_name])
            std_value = np.std(results[metric_name])
            logger.info(f"{metric_name}: {mean_value:.4f} ± {std_value:.4f}")
    
    return results

def grid_search(model_class,
                interactions: Dict[str, Any],
                param_grid: Dict[str, List[Any]],
                n_splits: int = 5) -> Dict[str, Any]:
    """
    Поиск оптимальных гиперпараметров
    
    Args:
        model_class: Класс модели рекомендаций
        interactions: Словарь с взаимодействиями
        param_grid: Сетка параметров для поиска
        n_splits: Количество фолдов для кросс-валидации
        
    Returns:
        Словарь с лучшими параметрами и результатами
    """
    best_score = -np.inf
    best_params = None
    results = []
    
    # Генерация всех комбинаций параметров
    from itertools import product
    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())
    
    for params in product(*param_values):
        param_dict = dict(zip(param_names, params))
        logger.info(f"Тестирование параметров: {param_dict}")
        
        # Кросс-валидация
        cv_results = cross_validate(
            model_class,
            interactions,
            n_splits=n_splits,
            **param_dict
        )
        
        # Усреднение метрик
        mean_ndcg = np.mean(cv_results['ndcg'])
        
        results.append({
            'params': param_dict,
            'score': mean_ndcg
        })
        
        if mean_ndcg > best_score:
            best_score = mean_ndcg
            best_params = param_dict
            
    logger.info(f"Лучшие параметры: {best_params}")
    logger.info(f"Лучший NDCG: {best_score:.4f}")
    
    return {
        'best_params': best_params,
        'best_score': best_score,
        'all_results': results
    } 