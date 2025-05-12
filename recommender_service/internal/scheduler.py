import logging
import asyncio
from datetime import datetime
import croniter

from recommender_service.internal.data.factory import DataFactory
from recommender_service.internal.service.recommender_service import RecommenderService

logger = logging.getLogger(__name__)

class ModelScheduler:
    """Планировщик для автоматического обучения моделей"""
    
    def __init__(self):
        self._config_service = DataFactory.get_config_service()
        self._recommender_service = RecommenderService()
        self._running = False
        
    async def start(self):
        """Запуск планировщика"""
        self._running = True
        while self._running:
            try:
                # Получаем все активные конфигурации
                configs = await self._config_service.list_configs(active_only=True)
                
                for config in configs:
                    # Проверяем расписание
                    if not config.train_schedule:
                        continue
                        
                    cron = croniter.croniter(config.train_schedule, datetime.utcnow())
                    next_run = cron.get_next(datetime)
                    
                    if next_run <= datetime.utcnow():
                        logger.info(f"Запуск обучения модели для конфигурации {config.config_id}")
                        try:
                            await self._recommender_service.train_model(config.config_id)
                        except Exception as e:
                            logger.error(f"Ошибка при обучении модели {config.config_id}: {e}")
                            
            except Exception as e:
                logger.error(f"Ошибка в планировщике: {e}")
                
            # Ждем 1 минуту перед следующей проверкой
            await asyncio.sleep(60)
            
    def stop(self):
        """Остановка планировщика"""
        self._running = False 