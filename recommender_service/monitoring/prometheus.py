from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from aiohttp import web
import logging

logger = logging.getLogger(__name__)

async def metrics_handler(request):
    """
    Обработчик для эндпоинта метрик Prometheus
    
    Args:
        request: HTTP запрос
        
    Returns:
        HTTP ответ с метриками
    """
    try:
        return web.Response(
            body=generate_latest(),
            content_type=CONTENT_TYPE_LATEST
        )
    except Exception as e:
        logger.error(f"Ошибка при генерации метрик: {e}")
        return web.Response(status=500)

def setup_metrics(app):
    """
    Настройка эндпоинта метрик в приложении
    
    Args:
        app: Экземпляр aiohttp приложения
    """
    app.router.add_get('/metrics', metrics_handler)
    logger.info("Метрики Prometheus доступны по адресу /metrics") 