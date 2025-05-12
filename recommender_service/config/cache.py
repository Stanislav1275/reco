from typing import Optional, Any
import json
import redis
from config.settings import settings

class RedisCache:
    def __init__(self):
        """Инициализация Redis клиента"""
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
    
    def get(self, key: str) -> Optional[Any]:
        """
        Получение значения из кеша
        
        Args:
            key: Ключ для получения значения
            
        Returns:
            Значение из кеша или None, если ключ не найден
        """
        value = self.redis_client.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Сохранение значения в кеш
        
        Args:
            key: Ключ для сохранения
            value: Значение для сохранения
            ttl: Время жизни в секундах (по умолчанию из настроек)
            
        Returns:
            True если успешно сохранено, False в противном случае
        """
        if ttl is None:
            ttl = settings.CACHE_TTL
            
        try:
            if not isinstance(value, (str, int, float, bool)):
                value = json.dumps(value)
            return self.redis_client.set(key, value, ex=ttl)
        except (TypeError, ValueError):
            return False
    
    def delete(self, key: str) -> bool:
        """
        Удаление значения из кеша
        
        Args:
            key: Ключ для удаления
            
        Returns:
            True если успешно удалено, False в противном случае
        """
        return bool(self.redis_client.delete(key))
    
    def exists(self, key: str) -> bool:
        """
        Проверка существования ключа в кеше
        
        Args:
            key: Ключ для проверки
            
        Returns:
            True если ключ существует, False в противном случае
        """
        return bool(self.redis_client.exists(key))
    
    def clear(self) -> None:
        """Очистка всего кеша"""
        self.redis_client.flushdb()

# Создаем глобальный экземпляр кеша
cache = RedisCache() 