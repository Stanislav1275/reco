# Локальная разработка с базами данных

Для локальной разработки можно запустить необходимые базы данных через Docker.

## Запуск всех баз данных

```bash
docker-compose -f docker-compose.mongodb.yml -f docker-compose.redis.yml -f docker-compose.mysql.yml up -d
```

## Запуск отдельных баз данных

### MongoDB
```bash
docker-compose -f docker-compose.mongodb.yml up -d
```

### Redis
```bash
docker-compose -f docker-compose.redis.yml up -d
```

### MySQL
```bash
docker-compose -f docker-compose.mysql.yml up -d
```

## Остановка всех баз данных

```bash
docker-compose -f docker-compose.mongodb.yml -f docker-compose.redis.yml -f docker-compose.mysql.yml down
```

## Переменные окружения для локальной разработки

Создайте файл `.env` в корне проекта со следующими переменными:

```env
# MongoDB
MONGODB_HOST=localhost
MONGODB_PORT=27017
MONGODB_DATABASE=recommender
MONGODB_USER=recommender_user
MONGODB_PASSWORD=recommender_pass

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=redis_pass
REDIS_DB=0

# gRPC
GRPC_PORT=50051

# Логирование
LOG_LEVEL=INFO

# Директория для датасетов
DATASET_DIR=./data/datasets

# Внешняя БД
EXTERNAL_DB_HOST=localhost
EXTERNAL_DB_PORT=3306
EXTERNAL_DB_NAME=external_db
EXTERNAL_DB_USER=external_user
EXTERNAL_DB_PASSWORD=external_pass
```

## Запуск приложения

1. Убедитесь, что у вас установлен Python 3.11:
```bash
python --version  # Должно показать Python 3.11.x
```

2. Создайте и активируйте виртуальное окружение:
```bash
python -m venv .venv
source .venv/bin/activate  # для Linux/Mac
.venv\Scripts\activate     # для Windows
```

3. Обновите pip до последней версии:
```bash
python -m pip install --upgrade pip
```

4. Установите зависимости:
```bash
pip install -r requirements.txt
```

5. Запустите приложение:
```bash
python -m recommender_service.main
``` 