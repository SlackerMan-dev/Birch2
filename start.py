#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Импортируем приложение
from app import app, db

if __name__ == "__main__":
    # Создаем таблицы, если их нет
    with app.app_context():
        try:
            db.create_all()
            print("✓ База данных инициализирована")
        except Exception as e:
            print(f"⚠️ Ошибка инициализации БД: {e}")
    
    # Получаем порт из переменной окружения или используем 8080
    port = int(os.environ.get('PORT', 8080))
    print(f"🚀 Запуск приложения на порту {port}")
    
    # Запускаем приложение
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        threaded=True
    ) 