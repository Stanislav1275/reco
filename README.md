# Recommender Service

## Запуск проекта

1. Создайте файл `.env` в директории `recommender_service`:
```env
# MongoDB
MONGODB_HOST=mongodb
MONGODB_PORT=27017
MONGODB_NAME=recommender_db
MONGODB_USER=user
MONGODB_PASSWORD=password

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# gRPC
GRPC_PORT=50051

# Логирование
LOG_LEVEL=INFO

# Внешняя БД (только чтение)
EXTERNAL_DB_HOST=external_db
EXTERNAL_DB_PORT=3306
EXTERNAL_DB_NAME=manga_db
EXTERNAL_DB_USER=user
EXTERNAL_DB_PASSWORD=password
```

2. Запустите сервисы:
```bash
docker-compose up -d
```

3. Проверьте логи:
```bash
docker-compose logs -f recommender
```

## Структура проекта

```
recommender_service/
├── config/
│   └── internal/
│       └── models.py
├── internal/
│   ├── data/
│   │   ├── factory.py
│   │   └── service.py
│   ├── service/
│   │   └── recommender_service.py
│   └── scheduler.py
├── proto/
│   └── recommender.proto
└── main.py
```

## API

Сервис предоставляет следующие gRPC методы:

- `GetRecommendations` - получение рекомендаций для пользователя
- `TrainModel` - обучение модели
- `GetConfigs` - получение конфигураций
- `GetModelMetrics` - получение метрик модели

## Остановка

Для остановки сервиса выполните:

```bash
docker-compose down
```