from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field
from enum import Enum

class Platform(str, Enum):
    """Платформы для рекомендательной системы"""
    N = "N"
    M = "M"

class FilterCondition(BaseModel):
    """Условие фильтрации для модели"""
    field: str
    operator: str
    value: Any
    description: str

class ModelConfig(BaseModel):
    """Конфигурация модели"""
    config_id: str = Field(..., description="Уникальный идентификатор конфигурации")
    name: str = Field(..., description="Название конфигурации")
    description: Optional[str] = Field(None, description="Описание конфигурации")
    site_ids: List[int] = Field(..., description="Список ID сайтов")
    active: bool = Field(True, description="Активна ли конфигурация")
    active_model_version: Optional[str] = Field(None, description="Активная версия модели")
    model_params: Dict[str, Any] = Field(default_factory=dict, description="Параметры модели")
    retrain_interval: int = Field(3600, description="Интервал переобучения в секундах")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ModelMetrics(BaseModel):
    """Метрики модели"""
    model_name: str = Field(..., description="Название модели")
    version: str = Field(..., description="Версия модели")
    metrics: Dict[str, float] = Field(..., description="Метрики")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class UserFeatures(BaseModel):
    """Признаки пользователя"""
    user_id: int
    features: Dict[str, float]
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class TitleFeatures(BaseModel):
    """Признаки произведения"""
    title_id: int
    features: Dict[str, float]
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class InteractionMatrix(BaseModel):
    """Матрица взаимодействий"""
    matrix_type: str  # 'user_title', 'title_title', etc.
    data: Dict[str, Any]  # Словарь с данными матрицы
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ModelCheckpoint(BaseModel):
    """Чекпоинт модели"""
    model_name: str = Field(..., description="Название модели")
    version: str = Field(..., description="Версия модели")
    checkpoint_data: Dict[str, Any] = Field(..., description="Данные чекпоинта")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class TrainingHistory(BaseModel):
    """История обучения"""
    model_name: str = Field(..., description="Название модели")
    version: str = Field(..., description="Версия модели")
    start_time: datetime = Field(..., description="Время начала обучения")
    end_time: datetime = Field(..., description="Время окончания обучения")
    config: Dict[str, Any] = Field(..., description="Конфигурация на момент обучения") 