#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from config import config

# Создаем Flask приложение
app = Flask(__name__)

# Настраиваем конфигурацию
config_name = os.environ.get('FLASK_CONFIG', 'production')
app.config.from_object(config[config_name])

# Инициализируем расширения
db = SQLAlchemy(app)
CORS(app)

# Импортируем маршруты после создания приложения
from app import *

if __name__ == "__main__":
    # Создаем таблицы, если их нет
    with app.app_context():
        db.create_all()
    
    # Запускаем приложение
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=False) 