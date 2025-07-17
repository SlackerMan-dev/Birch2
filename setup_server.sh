#!/bin/bash

echo🚀 Настройка сервера для развертывания приложения..."

# Обновление системы
echo "📦 Обновление системы..."
apt update && apt upgrade -y

# Установка необходимого ПО
echo "🔧 Установка необходимого ПО..."
apt install python3 python3pip python3-venv nginx supervisor mysql-client -y

# Создание пользователя webapp
echo "👤 Создание пользователя webapp..."
adduser --disabled-password --gecos webapp
usermod -aG sudo webapp

# Создание директорий
echo 📁Создание директорий..."
mkdir -p /home/webapp/accounting_app
mkdir -p /var/log/accounting_app
chown -R webapp:webapp /home/webapp/accounting_app
chown -R webapp:webapp /var/log/accounting_app

# Настройка Nginx
echo "🌐 Настройка Nginx...cat > /etc/nginx/sites-available/accounting_app << EOFerver[object Object]    listen 80
    server_name _;

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
EOF

# Активация конфигурации Nginx
ln -sf /etc/nginx/sites-available/accounting_app /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Настройка Supervisor
echo "⚙️ Настройка Supervisor...
cat > /etc/supervisor/conf.d/accounting_app.conf << 'EOF
[program:accounting_app]
command=/home/webapp/accounting_app/venv/bin/gunicorn --workers 3 --bind127.0.1wsgi:app
directory=/home/webapp/accounting_app
user=webapp
autostart=true
autorestart=true
stderr_logfile=/var/log/accounting_app/err.log
stdout_logfile=/var/log/accounting_app/out.log
EOF

# Перезапуск сервисов
echo 🔄 Перезапуск сервисов..."
supervisorctl reread
supervisorctl update
systemctl reload nginx

echo ✅ Настройка сервера завершена!echo ""
echo 📋 Следующие шаги:echo1зите файлы проекта в /home/webapp/accounting_app/echo2.Настройте виртуальное окружение:"
echo "   cd /home/webapp/accounting_appecho    python3 -m venv venv"
echo "   source venv/bin/activate"
echo    pip install -r requirements.txtecho 3. Настройте базу данных и конфигурациюecho4. Запустите приложение: sudo supervisorctl start accounting_app" 