from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator

from config.database import db_config

# Создаем движок для внутренней БД
engine = db_config.create_internal_engine()

# Создаем фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Контекстный менеджер для работы с сессией БД.
    Автоматически закрывает сессию после использования.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db() -> None:
    """
    Инициализация базы данных:
    1. Создает все таблицы
    2. Создает начальные конфигурации
    """
    from internal.models.models import Base
    
    # Создаем все таблицы
    Base.metadata.create_all(bind=engine)
    
    # Создаем начальные конфигурации
    with get_db() as db:
        from internal.models.models import Config
        
        # Проверяем, есть ли уже конфигурации
        if db.query(Config).first() is None:
            # Создаем базовую конфигурацию
            default_config = Config(
                name="default",
                description="Базовая конфигурация рекомендательной системы",
                model_params={
                    "learning_rate": 0.05,
                    "loss": "warp",
                    "learning_schedule": "adagrad",
                    "no_components": 32,
                    "max_sampled": 10
                },
                blacklist_rules={
                    "min_rating": 3.0,
                    "min_views": 100,
                    "exclude_genres": [],
                    "exclude_categories": []
                },
                age_restrictions={
                    "min_age": 0,
                    "max_age": 100
                },
                platform_settings={
                    "cache_ttl": 3600,
                    "recommendations_cache_ttl": 1800
                }
            )
            db.add(default_config)
            db.commit() 