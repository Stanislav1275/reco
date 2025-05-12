from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # External MySQL database settings
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER: str = os.getenv("MYSQL_USER", "user")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "password")
    MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "manga_db")
    MYSQL_URL: str = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
    
    # Internal MongoDB settings
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "recommender_db")
    
    # Redis settings
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Logging settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "DEBUG")
    
    # Recommendation system settings
    MIN_VOTES: int = int(os.getenv("MIN_VOTES", "100"))
    USERS_LIMIT: int = int(os.getenv("USERS_LIMIT", "1000000"))
    DAYS: int = int(os.getenv("DAYS", "1000000"))
    
    # Performance settings
    OPENBLAS_NUM_THREADS: int = int(os.getenv("OPENBLAS_NUM_THREADS", "1"))
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "4"))
    
    # Feature weights
    BOOKMARK_WEIGHTS: dict = {
        1: 7.0,  # Избранное
        2: 8.0,  # Читаю
        3: 7.0,  # Прочитано
        4: -0.1, # Отложено
        5: 3.0,  # Брошено
        6: -0.1, # Не интересно
    }
    
    # Temporal decay settings
    TEMPORAL_DECAY_OMEGA: float = float(os.getenv("TEMPORAL_DECAY_OMEGA", "0.01"))
    TEMPORAL_DECAY_MAX: float = float(os.getenv("TEMPORAL_DECAY_MAX", "0.7"))
    
    # Paid content boost
    PAID_CONTENT_BOOST: float = float(os.getenv("PAID_CONTENT_BOOST", "1.2"))
    
    # Cache settings
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour
    
    class Config:
        env_file = ".env"

settings = Settings() 