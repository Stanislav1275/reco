import os
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в PYTHONPATH
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from internal.database import init_db
from config.database import db_config

def main():
    """
    Скрипт для инициализации базы данных.
    Создает все необходимые таблицы и начальные данные.
    """
    print("Инициализация базы данных...")
    
    # Проверяем подключение к БД
    try:
        engine = db_config.create_internal_engine()
        with engine.connect() as conn:
            print("Подключение к базе данных успешно установлено")
    except Exception as e:
        print(f"Ошибка подключения к базе данных: {e}")
        sys.exit(1)
    
    # Инициализируем БД
    try:
        init_db()
        print("База данных успешно инициализирована")
    except Exception as e:
        print(f"Ошибка при инициализации базы данных: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 