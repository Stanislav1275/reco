from typing import Dict, Any
import os
from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError

class ReadOnlySessionError(Exception):
    """Исключение при попытке записи в read-only сессию"""
    pass

class DatabaseConfig:
    def __init__(self):
        self.external_db_config = {
            'host': os.getenv('EXTERNAL_DB_HOST', 'localhost'),
            'port': int(os.getenv('EXTERNAL_DB_PORT', 3306)),
            'database': os.getenv('EXTERNAL_DB_NAME', 'manga_db'),
            'user': os.getenv('EXTERNAL_DB_USER', 'user'),
            'password': os.getenv('EXTERNAL_DB_PASSWORD', 'password'),
        }
        
        self.internal_db_config = {
            'host': os.getenv('INTERNAL_DB_HOST', 'localhost'),
            'port': int(os.getenv('INTERNAL_DB_PORT', 27017)),
            'database': os.getenv('INTERNAL_DB_NAME', 'recommender_db'),
            'user': os.getenv('INTERNAL_DB_USER', 'user'),
            'password': os.getenv('INTERNAL_DB_PASSWORD', 'password'),
        }
        
    def get_external_db_url(self) -> str:
        """Получение URL для подключения к внешней MySQL БД"""
        return f"mysql+pymysql://{self.external_db_config['user']}:{self.external_db_config['password']}@{self.external_db_config['host']}:{self.external_db_config['port']}/{self.external_db_config['database']}"
    
    def get_internal_db_url(self) -> str:
        """Получение URL для подключения к внутренней MongoDB"""
        auth = f"{self.internal_db_config['user']}:{self.internal_db_config['password']}@" if self.internal_db_config['user'] else ""
        return f"mongodb://{auth}{self.internal_db_config['host']}:{self.internal_db_config['port']}/{self.internal_db_config['database']}"
    
    def create_external_engine(self):
        """Создание движка для внешней MySQL БД (только чтение)"""
        engine = create_engine(
            self.get_external_db_url(),
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800
        )
        
        # Запрещаем операции записи
        @event.listens_for(engine, 'before_execute')
        def before_execute(conn, clauseelement, multiparams, params):
            if str(clauseelement).lower().startswith(('insert', 'update', 'delete', 'drop', 'alter', 'create')):
                raise ReadOnlySessionError("Запись в external_db запрещена")
        
        return engine
    
    def create_internal_client(self):
        """Создание клиента для внутренней MongoDB"""
        return AsyncIOMotorClient(self.get_internal_db_url())

# Создаем глобальные подключения
db_config = DatabaseConfig()
external_engine = db_config.create_external_engine()
internal_client = db_config.create_internal_client()

# Создаем сессию для MySQL (только чтение)
ExternalSession = sessionmaker(bind=external_engine) 