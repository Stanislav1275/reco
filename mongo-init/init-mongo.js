db = db.getSiblingDB('recommender');

// Создаем коллекции
db.createCollection('model_configs');
db.createCollection('model_metrics');
db.createCollection('user_features');
db.createCollection('title_features');
db.createCollection('interaction_matrices');
db.createCollection('model_checkpoints');
db.createCollection('training_history');

// Создаем индексы
db.model_configs.createIndex({ "config_id": 1 }, { unique: true });
db.model_configs.createIndex({ "site_ids": 1 });
db.model_configs.createIndex({ "is_active": 1 });

db.model_metrics.createIndex({ "model_name": 1, "timestamp": -1 });
db.model_metrics.createIndex({ "version": 1 });

db.user_features.createIndex({ "user_id": 1 }, { unique: true });
db.user_features.createIndex({ "updated_at": -1 });

db.title_features.createIndex({ "title_id": 1 }, { unique: true });
db.title_features.createIndex({ "updated_at": -1 });

db.interaction_matrices.createIndex({ "matrix_type": 1, "created_at": -1 });

db.model_checkpoints.createIndex({ "model_name": 1, "version": 1 }, { unique: true });
db.model_checkpoints.createIndex({ "created_at": -1 });

db.training_history.createIndex({ "model_name": 1, "start_time": -1 });
db.training_history.createIndex({ "status": 1 });

// Создаем пользователя для приложения
db.createUser({
  user: 'recommender_user',
  pwd: 'recommender_pass',
  roles: [
    { role: 'readWrite', db: 'recommender' }
  ]
}); 