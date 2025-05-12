FROM python:3.9-slim

WORKDIR /app

# Установка зависимостей
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