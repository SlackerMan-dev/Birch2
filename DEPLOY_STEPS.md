# 🚀 Простая инструкция запуска проекта на Timeweb Cloud

## ✅ Что у вас уже есть:
- Сервер Ubuntu на Timeweb Cloud
- База данных MySQL
- Папка с проектом
- SSH подключение

## 📋 Пошаговая инструкция:

### Шаг1ерка папки проекта
```bash
# Проверьте, что вы в папке с проектом
pwd
ls -la
```

Вы должны увидеть файлы: `app.py`, `requirements.txt`, `templates/` и другие.

### Шаг 2: Установка Python и зависимостей
```bash
# Обновление системы
sudo apt update

# Установка Python и pip
sudo apt install python3 python3pip python3-venv -y

# Создание виртуального окружения
python3 -m venv venv

# Активация виртуального окружения
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt
```

### Шаг3тройка базы данных
1. **Запишите данные вашей базы данных:**
   - Хост (например: `mysql.timeweb.ru`)
   - Пользователь (например: `username`)
   - Пароль (например: `password123`)
   - База данных (например: `accounting_system`)

2*Создайте файл конфигурации:**
```bash
nano config.py
```

3. **Вставьте в файл:**
```python
import os

class Config:
    SECRET_KEY =your-secret-key-here'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH =16 *1024 *1024
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    ADMIN_PASSWORD =Blalala2

class ProductionConfig(Config):
    DEBUG = False
    # ЗАМЕНИТЕ НА ВАШИ ДАННЫЕ БАЗЫ ДАННЫХ
    SQLALCHEMY_DATABASE_URI =mysql+pymysql://ВАШ_ПОЛЬЗОВАТЕЛЬ:ВАШ_ПАРОЛЬ@ВАШ_ХОСТ:3306АША_БАЗА_ДАННЫХ'

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///arbitrage_reports.db'

config = [object Object]development': DevelopmentConfig,production': ProductionConfig,
    'default': ProductionConfig
}
```

4. **Сохраните файл:** `Ctrl+X`, затем `Y`, затем `Enter`

### Шаг 4 Создание таблиц в базе данных1. **Откройте phpMyAdmin** в панели Timeweb Cloud2. **Войдите в вашу базу данных**3. **Перейдите на вкладку SQL"**4. **Скопируйте и вставьте содержимое файла `mysql_schema.sql`**
5. **Нажмите Выполнить"**

### Шаг5Создание папки для загрузок
```bash
# Создание папки uploads
mkdir uploads

# Проверка создания
ls -la
```

### Шаг 6: Тестовый запуск
```bash
# Убедитесь, что виртуальное окружение активировано
source venv/bin/activate

# Запуск приложения
python app.py
```

Если все работает, вы увидите что-то вроде:
```
 * Running on http://12700.1:500
```

### Шаг 7: Остановка тестового запуска
Нажмите `Ctrl+C` для остановки

### Шаг 8 Настройка Nginx (веб-сервер)
```bash
# Установка Nginx
sudo apt install nginx -y

# Создание конфигурации
sudo nano /etc/nginx/sites-available/accounting_app
```

**Вставьте в файл:**
```nginx
server[object Object]    listen 80
    server_name ВАШ_IP_АДРЕС_СЕРВЕРА;  # Замените на ваш IP

    location / {
        proxy_pass http://127.000
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /uploads[object Object]       alias /home/ВАШ_ПОЛЬЗОВАТЕЛЬ/accounting_app/uploads;
    }
}
```

**Сохраните:** `Ctrl+X`, `Y`, `Enter`

```bash
# Активация конфигурации
sudo ln -sf /etc/nginx/sites-available/accounting_app /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### Шаг 9: Настройка Supervisor (автозапуск)
```bash
# Установка Supervisor
sudo apt install supervisor -y

# Создание конфигурации
sudo nano /etc/supervisor/conf.d/accounting_app.conf
```

**Вставьте в файл:**
```ini
[program:accounting_app]
command=/home/ВАШ_ПОЛЬЗОВАТЕЛЬ/accounting_app/venv/bin/gunicorn --workers 3 --bind127.0.1wsgi:app
directory=/home/ВАШ_ПОЛЬЗОВАТЕЛЬ/accounting_app
user=ВАШ_ПОЛЬЗОВАТЕЛЬ
autostart=true
autorestart=true
stderr_logfile=/var/log/accounting_app/err.log
stdout_logfile=/var/log/accounting_app/out.log
```

**Сохраните:** `Ctrl+X`, `Y`, `Enter`

```bash
# Создание папки для логов
sudo mkdir -p /var/log/accounting_app
sudo chown ВАШ_ПОЛЬЗОВАТЕЛЬ:ВАШ_ПОЛЬЗОВАТЕЛЬ /var/log/accounting_app

# Перезапуск Supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start accounting_app
```

### Шаг 10: Проверка работы
```bash
# Проверка статуса
sudo supervisorctl status accounting_app

# Просмотр логов
tail -f /var/log/accounting_app/out.log
```

### Шаг 11: Открытие в браузере
Откройте в браузере: `http://ВАШ_IP_АДРЕС_СЕРВЕРА`

## 🔧 Полезные команды:

### Проверка статуса:
```bash
sudo supervisorctl status accounting_app
```

### Просмотр логов:
```bash
tail -f /var/log/accounting_app/out.log
```

### Перезапуск приложения:
```bash
sudo supervisorctl restart accounting_app
```

### Перезапуск Nginx:
```bash
sudo systemctl reload nginx
```

## ❗ Важные замечания:

1. **Замените `ВАШ_ПОЛЬЗОВАТЕЛЬ`** на ваше имя пользователя на сервере
2. **Замените `ВАШ_IP_АДРЕС_СЕРВЕРА`** на IP вашего сервера
3. **Замените данные базы данных** в `config.py` на ваши реальные
4. **Убедитесь, что порт 80 открыт** в настройках Timeweb Cloud

## 🎉 Готово!
Ваше приложение теперь работает на облачном сервере! 