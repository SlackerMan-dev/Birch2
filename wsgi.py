#!/usr/bin/env python3
""
WSGI entry point для развертывания на продакшн сервере
""
import os
import sys

# Добавляем путь к проекту в sys.path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

# Импортируем приложение
from app import app

if __name__ == "__main__":
    app.run() 