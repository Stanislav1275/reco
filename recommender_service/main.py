import asyncio
import logging
import signal
from concurrent.futures import ThreadPoolExecutor

import grpc
from grpc_reflection.v1alpha import reflection

from recommender_service.internal.data.factory import DataFactory
from recommender_service.internal.scheduler import ModelScheduler
from recommender_service.proto import recommender_pb2_grpc
from recommender_service.proto.recommender_pb2 import DESCRIPTOR

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RecommenderServicer(recommender_pb2_grpc.RecommenderServiceServicer):
    """gRPC сервис для рекомендаций"""
    
    def __init__(self):
        self._recommender_service = RecommenderService()
        
    async def GetRecommendations(self, request, context):
        """Получение рекомендаций для пользователя"""
        try:
            recommendations = await self._recommender_service.get_recommendations(
                user_id=request.user_id,
                config_id=request.config_id,
                limit=request.limit,
                filter_viewed=request.filter_viewed
            )
            
            return recommender_pb2.RecommendationResponse(
                items=[
                    recommender_pb2.RecommendationItem(
                        title_id=item["title_id"],
                        score=item["score"]
                    )
                    for item in recommendations
                ]
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return recommender_pb2.RecommendationResponse()
            
    async def TrainModel(self, request, context):
        """Обучение модели"""
        try:
            result = await self._recommender_service.train_model(
                config_id=request.config_id,
                force=request.force
            )
            
            return recommender_pb2.TrainResponse(
                status=result["status"],
                message=result["message"],
                model_version=result["model_version"]
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return recommender_pb2.TrainResponse()
            
    async def GetConfigs(self, request, context):
        """Получение конфигураций"""
        try:
            configs = await self._recommender_service.get_configs(
                site_ids=request.site_ids,
                active_only=request.active_only
            )
            
            return recommender_pb2.ConfigResponse(
                configs=[
                    recommender_pb2.ModelConfig(
                        config_id=config.config_id,
                        site_ids=config.site_ids,
                        name=config.name,
                        description=config.description,
                        train_schedule=config.train_schedule,
                        model_params=config.model_params,
                        filters=[
                            recommender_pb2.FilterCondition(
                                field=f.field,
                                operator=f.operator,
                                value=str(f.value),
                                description=f.description
                            )
                            for f in config.filters
                        ],
                        last_train_time=config.last_train_time,
                        active_model_version=config.active_model_version,
                        is_active=config.is_active
                    )
                    for config in configs
                ]
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return recommender_pb2.ConfigResponse()
            
    async def GetModelMetrics(self, request, context):
        """Получение метрик модели"""
        try:
            metrics = await self._recommender_service.get_model_metrics(
                config_id=request.config_id,
                model_version=request.model_version
            )
            
            return recommender_pb2.MetricsResponse(
                metrics=metrics["metrics"],
                model_version=metrics["model_version"],
                timestamp=metrics["timestamp"]
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return recommender_pb2.MetricsResponse()

async def serve():
    """Запуск gRPC сервера"""
    server = grpc.aio.server()
    
    # Добавляем сервис
    recommender_pb2_grpc.add_RecommenderServiceServicer_to_server(
        RecommenderServicer(),
        server
    )
    
    # Добавляем reflection
    SERVICE_NAMES = (
        DESCRIPTOR.services_by_name['RecommenderService'].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(SERVICE_NAMES, server)
    
    # Запускаем сервер
    server.add_insecure_port('[::]:50051')
    await server.start()
    
    # Запускаем планировщик
    scheduler = ModelScheduler()
    scheduler_task = asyncio.create_task(scheduler.start())
    
    # Обработка сигналов для graceful shutdown
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig,
            lambda: asyncio.create_task(shutdown(server, scheduler))
        )
    
    logger.info("Сервер запущен на порту 50051")
    await server.wait_for_termination()

async def shutdown(server, scheduler):
    """Graceful shutdown"""
    logger.info("Получен сигнал завершения")
    
    # Останавливаем планировщик
    scheduler.stop()
    
    # Закрываем соединения
    DataFactory.close_connections()
    
    # Останавливаем сервер
    await server.stop(grace=None)
    
    # Завершаем все задачи
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    await asyncio.gather(*tasks, return_exceptions=True)
    
    logger.info("Сервер остановлен")

if __name__ == '__main__':
    asyncio.run(serve()) 