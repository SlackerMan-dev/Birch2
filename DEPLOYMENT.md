# Инструкция по развертыванию на Timeweb Cloud

## 1. Подготовка проекта

### 1.1 Обновление requirements.txt
Добавьте следующие зависимости для работы с MySQL:
```
Flask==2.3.3Flask-SQLAlchemy==3.0.5
Flask-CORS==4.0pandas==2.1.1xl==31.2
requests==2.31.0erkzeug==2.3.7SQLAlchemy==221
python-dateutil==2.8
pytz==2023.3.post1alembic==1.12xlrd==2.0.1Добавить для MySQL
PyMySQL==110
cryptography==4107

### 12оздание файла .env для переменных окружения
Создайте файл `.env` в корне проекта:
```
# База данных
DB_HOST=your_mysql_host
DB_NAME=accounting_system
DB_USER=your_username
DB_PASS=your_password
DB_PORT=3306# Безопасность
SECRET_KEY=your-secret-key-here
ADMIN_PASSWORD=your-admin-password

# Настройки приложения
FLASK_ENV=production
FLASK_DEBUG=0
```

##2тройка базы данных MySQL

###2.1здание базы данных
```sql
CREATE DATABASE accounting_system CHARACTER SET utf8mb4TE utf8mb4_unicode_ci;
```

### 2.2 Создание пользователя
```sql
CREATE USER your_username'@'%' IDENTIFIED BYyour_password';
GRANT ALL PRIVILEGES ON accounting_system.* TO your_username'@%';
FLUSH PRIVILEGES;
```

### 20.3Миграция данных из SQLite в MySQL
1. Экспортируйте данные из SQLite:
```bash
python export_sqlite_data.py
```

2. Импортируйте данные в MySQL:
```bash
python import_mysql_data.py
```

## 3. Развертывание на Timeweb Cloud

### 3.1 Создание виртуального сервера1. Войдите в панель управления Timeweb Cloud2 Создайте новый виртуальный сервер:
   - ОС: Ubuntu 22.04LTS
   - RAM: минимум 2
   - CPU: минимум1ро
   - Диск: минимум20GB

###3.2 Подключение к серверу
```bash
ssh root@your_server_ip
```

### 3.3 Установка необходимого ПО
```bash
# Обновление системы
apt update && apt upgrade -y

# Установка Python и pip
apt install python3 python3pip python3-venv -y

# Установка MySQL клиента
apt install mysql-client -y

# Установка Nginx
apt install nginx -y

# Установка Supervisor для управления процессами
apt install supervisor -y
```

### 3.4 Создание пользователя для приложения
```bash
adduser webapp
usermod -aG sudo webapp
```

### 3.5 Клонирование проекта
```bash
cd /home/webapp
git clone your_repository_url accounting_app
cd accounting_app
```

###3.6Настройка виртуального окружения
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3.7 Настройка переменных окружения
```bash
cp .env.example .env
nano .env
# Отредактируйте файл с вашими настройками
```

## 4 Настройка Nginx

### 4.1Создание конфигурации Nginx
Создайте файл `/etc/nginx/sites-available/accounting_app`:
```nginx
server[object Object]    listen 80  server_name your_domain.com;

    location / {
        proxy_pass http://127.000
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static[object Object]       alias /home/webapp/accounting_app/static;
    }

    location /uploads[object Object]       alias /home/webapp/accounting_app/uploads;
    }
}
```

###40.2ктивация конфигурации
```bash
ln -s /etc/nginx/sites-available/accounting_app /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

## 5. Настройка Supervisor

### 5.1Создание конфигурации Supervisor
Создайте файл `/etc/supervisor/conf.d/accounting_app.conf`:
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

### 5.2оздание директории для логов
```bash
mkdir -p /var/log/accounting_app
chown webapp:webapp /var/log/accounting_app
```

### 5.3 Перезапуск Supervisor
```bash
supervisorctl reread
supervisorctl update
supervisorctl start accounting_app
```

## 6 Настройка SSL (опционально)

### 6.1 Установка Certbot
```bash
apt install certbot python3-certbot-nginx -y
```

###6.2 Получение SSL сертификата
```bash
certbot --nginx -d your_domain.com
```

## 7 Проверка развертывания

### 71оверка статуса сервисов
```bash
supervisorctl status accounting_app
systemctl status nginx
```

### 70.2Проверка логов
```bash
tail -f /var/log/accounting_app/out.log
tail -f /var/log/accounting_app/err.log
```

### 70.3оверка подключения к базе данных
```bash
cd /home/webapp/accounting_app
source venv/bin/activate
python -c "from app import db; print('База данных подключена успешно)"
```

##8ервное копирование

### 81здание скрипта резервного копирования
Создайте файл `/home/webapp/backup.sh`:
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/home/webapp/backups"

mkdir -p $BACKUP_DIR

# Резервное копирование базы данных
mysqldump -h $DB_HOST -u $DB_USER -p$DB_PASS $DB_NAME > $BACKUP_DIR/db_backup_$DATE.sql

# Резервное копирование файлов
tar -czf $BACKUP_DIR/files_backup_$DATE.tar.gz /home/webapp/accounting_app/uploads

# Удаление старых резервных копий (старше 30дней)
find $BACKUP_DIR -name *.sql" -mtime +30 -delete
find $BACKUP_DIR -name*.tar.gz" -mtime +30 -delete
```

### 8.2 Настройка автоматического резервного копирования
```bash
chmod +x /home/webapp/backup.sh
crontab -e
# Добавьте строку для ежедневного резервного копирования в 2:02* * * /home/webapp/backup.sh
```

## 9. Мониторинг

### 9.1Установка мониторинга
```bash
apt install htop iotop -y
```

### 9.2тройка логирования
```bash
# Добавьте в /etc/logrotate.d/accounting_app
/home/webapp/accounting_app/logs/*.log {
    daily
    missingok
    rotate 52compress
    delaycompress
    notifempty
    create 644app webapp
}
```

## 10овление приложения

###10.1 Скрипт обновления
Создайте файл `/home/webapp/update.sh`:
```bash
#!/bin/bash
cd /home/webapp/accounting_app

# Остановка приложения
supervisorctl stop accounting_app

# Получение обновлений
git pull origin main

# Обновление зависимостей
source venv/bin/activate
pip install -r requirements.txt

# Применение миграций базы данных
python -c "from app import db; db.create_all()"

# Запуск приложения
supervisorctl start accounting_app

echoПриложение обновлено успешно!"
```

### 10.2рава на выполнение
```bash
chmod +x /home/webapp/update.sh
```

##11. Устранение неполадок

### 110.1Проверка логов
```bash
# Логи приложения
tail -f /var/log/accounting_app/out.log

# Логи Nginx
tail -f /var/log/nginx/error.log

# Логи Supervisor
tail -f /var/log/supervisor/supervisord.log
```

### 112ерезапуск сервисов
```bash
supervisorctl restart accounting_app
systemctl restart nginx
```

###11.3роверка портов
```bash
netstat -tlnp | grep :500tstat -tlnp | grep :80``

## 12 Безопасность

### 120.1Настройка файрвола
```bash
ufw allow 22allow80
ufw allow 443fw enable
```

### 122улярные обновления
```bash
# Добавьте в crontab
0 3 * 0 apt update && apt upgrade -y
```

## 13. Контакты для поддержки

При возникновении проблем:
1Проверьте логи: `/var/log/accounting_app/`
2. Проверьте статус сервисов: `supervisorctl status`
3. Проверьте подключение к базе данных
4. Обратитесь к документации Flask и Timeweb Cloud 