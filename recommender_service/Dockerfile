FROM python:3.9-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    pkg-config \
    default-libmysqlclient-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Обновление pip
RUN pip install --no-cache-dir --upgrade pip

# Установка зависимостей Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода и конфигурации
COPY . .

# Создание пользователя и директорий
RUN useradd -m recommender && \
    mkdir -p /app/data && \
    mkdir -p /app/data/datasets && \
    chown -R recommender:recommender /app

USER recommender

# Запуск сервиса
CMD ["python", "-m", "recommender_service.main"] 