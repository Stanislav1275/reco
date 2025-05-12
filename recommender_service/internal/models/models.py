from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Config(Base):
    __tablename__ = 'configs'
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Параметры модели
    model_params = Column(JSON)
    
    # Правила черного списка
    blacklist_rules = Column(JSON)
    
    # Возрастные ограничения
    age_restrictions = Column(JSON)
    
    # Настройки платформы
    platform_settings = Column(JSON)
    
    # Связи
    training_history = relationship("TrainingHistory", back_populates="config")
    metrics = relationship("Metrics", back_populates="config")

class TrainingHistory(Base):
    __tablename__ = 'training_history'
    
    id = Column(Integer, primary_key=True)
    config_id = Column(String, ForeignKey('configs.id'))
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    status = Column(String)  # 'running', 'completed', 'failed'
    error_message = Column(String)
    
    # Параметры обучения
    training_params = Column(JSON)
    
    # Связи
    config = relationship("Config", back_populates="training_history")
    metrics = relationship("Metrics", back_populates="training")

class Metrics(Base):
    __tablename__ = 'metrics'
    
    id = Column(Integer, primary_key=True)
    config_id = Column(String, ForeignKey('configs.id'))
    training_id = Column(Integer, ForeignKey('training_history.id'))
    metric_name = Column(String)
    metric_value = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    config = relationship("Config", back_populates="metrics")
    training = relationship("TrainingHistory", back_populates="metrics")

class ModelArtifact(Base):
    __tablename__ = 'model_artifacts'
    
    id = Column(Integer, primary_key=True)
    config_id = Column(String, ForeignKey('configs.id'))
    training_id = Column(Integer, ForeignKey('training_history.id'))
    artifact_path = Column(String)
    artifact_type = Column(String)  # 'model', 'embeddings', etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=False)
    
    # Метаданные артефакта
    metadata = Column(JSON) 