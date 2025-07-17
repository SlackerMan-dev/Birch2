# 🚀 Исправленная инструкция развертывания на Timeweb Cloud

## Проблема была в SQL коде - теперь исправлено!

### ✅ Что исправлено:
1. **Синтаксические ошибки в SQL** - все кавычки и запятые исправлены
2 **Правильные типы данных** - DECIMAL(15,2 вместо DECIMAL(15OT NULL
3. **Корректные значения по умолчанию** - все DEFAULT значения исправлены4**Правильные имена таблиц** - `order` в кавычках для избежания конфликтов

## 📋 Пошаговый план:

### Этап 1: Подготовка проекта
1. Создайте ZIP архив проекта2Убедитесь, что файл `mysql_schema.sql` содержит правильный SQL код
3. Обновите `requirements.txt` (уже сделано)

### Этап2: Создание сервера на Timeweb Cloud
1Зайдите на timeweb.cloud
2. Создайте виртуальный сервер:
   - ОС: Ubuntu 22.4LTS
   - RAM: 2 GB
   - CPU: 1ядро
   - Диск:20 GB3 Запишите IP адрес сервера

### Этап 3: Подключение к серверу
```bash
ssh root@IP_АДРЕС_СЕРВЕРА
```

### Этап 4 Настройка сервера
```bash
# Обновление системы
apt update && apt upgrade -y

# Установка необходимого ПО
apt install python3 python3pip python3-venv nginx supervisor mysql-client -y

# Создание пользователя
adduser webapp
usermod -aG sudo webapp

# Создание директорий
mkdir -p /home/webapp/accounting_app
mkdir -p /var/log/accounting_app
chown -R webapp:webapp /home/webapp/accounting_app
chown -R webapp:webapp /var/log/accounting_app
```

### Этап 5: Загрузка проекта
```bash
# Переключитесь на пользователя webapp
su - webapp

# Загрузите архив проекта и распакуйте в /home/webapp/accounting_app/
cd ~/accounting_app
```

### Этап 6: Настройка Python окружения
```bash
cd ~/accounting_app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Этап 7: Создание базы данных MySQL
1. В панели Timeweb Cloud создайте MySQL базу данных
2шите данные подключения:
   - Хост
   - Пользователь
   - Пароль
   - База данных: `accounting_system`

### Этап 8 Создание таблиц в MySQL
1. В панели Timeweb Cloud найдите вашу базу данных2ажмите phpMyAdminили Веб-консоль
3. Войдите с данными пользователя
4. Выберите базу данных `accounting_system`5Перейдите на вкладку "SQL"
6. Скопируйте и выполните содержимое файла `mysql_schema.sql`

### Этап 9астройка конфигурации приложения
Создайте файл `config.py`:
```python
import os

class Config:
    SECRET_KEY = os.environ.get(SECRET_KEY,dev-key-change-in-production')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH =16 *1024 *1024
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', Blalala2

class ProductionConfig(Config):
    DEBUG = False
    # ЗАМЕНИТЕ НА ВАШИ ДАННЫЕ БАЗЫ ДАННЫХ
    SQLALCHEMY_DATABASE_URI =mysql+pymysql://ВАШ_ПОЛЬЗОВАТЕЛЬ:ВАШ_ПАРОЛЬ@ВАШ_ХОСТ:3306/accounting_system'

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///arbitrage_reports.db'

config = [object Object]development': DevelopmentConfig,production': ProductionConfig,
    'default': DevelopmentConfig
}
```

### Этап 10: Настройка Nginx
```bash
# Создание конфигурации Nginx
sudo nano /etc/nginx/sites-available/accounting_app
```

Содержимое:
```nginx
server[object Object]    listen 80    server_name IP_АДРЕС_СЕРВЕРА;  # Замените на ваш IP

    location / {
        proxy_pass http://127.000
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /uploads[object Object]       alias /home/webapp/accounting_app/uploads;
    }
}
```

```bash
# Активация конфигурации
sudo ln -sf /etc/nginx/sites-available/accounting_app /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### Этап 11: Настройка Supervisor
```bash
# Создание конфигурации Supervisor
sudo nano /etc/supervisor/conf.d/accounting_app.conf
```

Содержимое:
```ini
[program:accounting_app]
command=/home/webapp/accounting_app/venv/bin/gunicorn --workers 3 --bind127.0.1wsgi:app
directory=/home/webapp/accounting_app
user=webapp
autostart=true
autorestart=true
stderr_logfile=/var/log/accounting_app/err.log
stdout_logfile=/var/log/accounting_app/out.log
```

```bash
# Перезапуск Supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start accounting_app
```

### Этап 12 Миграция данных (если нужно)
Если у вас есть данные в SQLite, используйте скрипт миграции:
```bash
cd ~/accounting_app
source venv/bin/activate
python migrate_to_mysql.py
```

### Этап 13: Проверка работы
1 Проверьте логи: `tail -f /var/log/accounting_app/out.log`2. Откройте в браузере: `http://IP_АДРЕС_СЕРВЕРА`
3. Проверьте статус: `sudo supervisorctl status accounting_app`

## 🔧 Полезные команды:
- **Проверка статуса**: `sudo supervisorctl status accounting_app`
- **Просмотр логов**: `tail -f /var/log/accounting_app/out.log`
- **Перезапуск**: `sudo supervisorctl restart accounting_app`
- **Проверка портов**: `netstat -tlnp | grep :8000## ❗ Важные замечания:
1. **Замените данные базы данных** в `config.py` на ваши реальные
2. **Замените IP адрес** в конфигурации Nginx
3. **Проверьте права доступа** к файлам и папкам4 **Сделайте резервную копию** перед миграцией данных

## 🎉 Готово!
Ваше приложение теперь работает на Timeweb Cloud с MySQL базой данных! 