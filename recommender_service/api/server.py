import logging
from concurrent import futures
import grpc
from typing import List, Dict, Any
import time

from config.settings import settings
from config.cache import cache
from internal.database import get_db
from internal.models.models import Config, ModelArtifact, Metrics
from recommender.base import BaseRecommender
from tasks.training import train_model
from tasks.metrics import collect_metrics
from proto import recommender_pb2, recommender_pb2_grpc
from monitoring.metrics import (
    RECOMMENDATION_REQUESTS, RECOMMENDATION_LATENCY,
    RECOMMENDATION_CACHE_HITS, RECOMMENDATION_CACHE_MISSES,
    track_time, track_errors
)

logger = logging.getLogger(__name__)

class RecommenderServicer(recommender_pb2_grpc.RecommenderServiceServicer):
    def __init__(self):
        """Инициализация сервиса рекомендаций"""
        self._load_active_model()
    
    def _load_active_model(self) -> None:
        """Загрузка активной модели из БД"""
        with get_db() as db:
            artifact = db.query(ModelArtifact).filter_by(is_active=True).first()
            if artifact:
                self.model = BaseRecommender.load(artifact.artifact_path)
            else:
                self.model = None
    
    @track_time(RECOMMENDATION_LATENCY, {'type': 'user_recommendations'})
    @track_errors(RECOMMENDATION_REQUESTS, {'type': 'user_recommendations'})
    def GetUserRecommendations(self, request, context):
        """
        Получение рекомендаций для пользователя
        
        Args:
            request: Запрос с ID пользователя и лимитом
            context: gRPC контекст
            
        Returns:
            Список рекомендованных произведений
        """
        try:
            # Проверяем кеш
            cache_key = f"user_recommendations:{request.user_id}:{request.limit}"
            cached_recommendations = cache.get(cache_key)
            if cached_recommendations:
                RECOMMENDATION_CACHE_HITS.labels(type='user_recommendations').inc()
                return recommender_pb2.GetUserRecommendationsResponse(
                    titles=[self._create_title_proto(t) for t in cached_recommendations]
                )
            
            RECOMMENDATION_CACHE_MISSES.labels(type='user_recommendations').inc()
            
            # Получаем рекомендации
            if not self.model:
                context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
                context.set_details("Модель не загружена")
                return recommender_pb2.GetUserRecommendationsResponse()
            
            recommendations = self.model.get_user_recommendations(
                user_id=request.user_id,
                limit=request.limit
            )
            
            # Кешируем результаты
            cache.set(cache_key, recommendations, ttl=settings.RECOMMENDATIONS_CACHE_TTL)
            
            return recommender_pb2.GetUserRecommendationsResponse(
                titles=[self._create_title_proto(t) for t in recommendations]
            )
            
        except Exception as e:
            logger.error(f"Ошибка при получении рекомендаций: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return recommender_pb2.GetUserRecommendationsResponse()
    
    @track_time(RECOMMENDATION_LATENCY, {'type': 'similar_titles'})
    @track_errors(RECOMMENDATION_REQUESTS, {'type': 'similar_titles'})
    def GetSimilarTitles(self, request, context):
        """
        Получение похожих произведений
        
        Args:
            request: Запрос с ID произведения и лимитом
            context: gRPC контекст
            
        Returns:
            Список похожих произведений
        """
        try:
            # Проверяем кеш
            cache_key = f"similar_titles:{request.title_id}:{request.limit}"
            cached_similar = cache.get(cache_key)
            if cached_similar:
                RECOMMENDATION_CACHE_HITS.labels(type='similar_titles').inc()
                return recommender_pb2.GetSimilarTitlesResponse(
                    titles=[self._create_title_proto(t) for t in cached_similar]
                )
            
            RECOMMENDATION_CACHE_MISSES.labels(type='similar_titles').inc()
            
            # Получаем похожие произведения
            if not self.model:
                context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
                context.set_details("Модель не загружена")
                return recommender_pb2.GetSimilarTitlesResponse()
            
            similar_titles = self.model.get_similar_items(
                item_id=request.title_id,
                limit=request.limit
            )
            
            # Кешируем результаты
            cache.set(cache_key, similar_titles, ttl=settings.RECOMMENDATIONS_CACHE_TTL)
            
            return recommender_pb2.GetSimilarTitlesResponse(
                titles=[self._create_title_proto(t) for t in similar_titles]
            )
            
        except Exception as e:
            logger.error(f"Ошибка при получении похожих произведений: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return recommender_pb2.GetSimilarTitlesResponse()
    
    def TrainModel(self, request, context):
        """
        Запуск обучения модели
        
        Args:
            request: Запрос с ID конфигурации
            context: gRPC контекст
            
        Returns:
            Результат запуска обучения
        """
        try:
            # Проверяем существование конфигурации
            with get_db() as db:
                config = db.query(Config).get(request.config_id)
                if not config:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details(f"Конфигурация {request.config_id} не найдена")
                    return recommender_pb2.TrainModelResponse()
            
            # Запускаем задачу обучения
            task = train_model.delay(request.config_id)
            
            return recommender_pb2.TrainModelResponse(
                task_id=task.id,
                status="started"
            )
            
        except Exception as e:
            logger.error(f"Ошибка при запуске обучения: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return recommender_pb2.TrainModelResponse()
    
    def GetMetrics(self, request, context):
        """
        Получение метрик модели
        
        Args:
            request: Запрос с ID конфигурации
            context: gRPC контекст
            
        Returns:
            Список метрик
        """
        try:
            with get_db() as db:
                metrics = db.query(Metrics).filter_by(
                    config_id=request.config_id
                ).order_by(Metrics.timestamp.desc()).limit(100).all()
                
                return recommender_pb2.GetMetricsResponse(
                    metrics=[
                        recommender_pb2.Metric(
                            name=m.metric_name,
                            value=m.metric_value,
                            timestamp=m.timestamp.isoformat()
                        )
                        for m in metrics
                    ]
                )
                
        except Exception as e:
            logger.error(f"Ошибка при получении метрик: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return recommender_pb2.GetMetricsResponse()
    
    def _create_title_proto(self, title: Dict[str, Any]) -> recommender_pb2.Title:
        """Создание proto-объекта для произведения"""
        return recommender_pb2.Title(
            id=title['id'],
            name=title['name'],
            score=title['score'],
            metadata=title.get('metadata', {})
        )

def serve():
    """Запуск gRPC сервера"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    recommender_pb2_grpc.add_RecommenderServiceServicer_to_server(
        RecommenderServicer(), server
    )
    server.add_insecure_port(f"{settings.GRPC_HOST}:{settings.GRPC_PORT}")
    server.start()
    logger.info(f"Сервер запущен на {settings.GRPC_HOST}:{settings.GRPC_PORT}")
    server.wait_for_termination()

if __name__ == '__main__':
    logging.basicConfig(level=settings.LOG_LEVEL)
    serve() 