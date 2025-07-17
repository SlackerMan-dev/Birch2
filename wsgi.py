#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from app import app, db

if __name__ == "__main__":
    # Создаем таблицы, если их нет
    with app.app_context():
        db.create_all()
    
    # Запускаем приложение
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=False) 