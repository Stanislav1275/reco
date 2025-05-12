FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# Копирование файлов зависимостей
COPY requirements.txt .

# Установка зависимостей Python
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Создание пользователя
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Создание необходимых директорий
RUN mkdir -p /app/data/datasets

# Запуск приложения
CMD ["python", "-m", "recommender_service.main"] 