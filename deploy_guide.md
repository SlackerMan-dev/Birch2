# 🚀 Пошаговая инструкция развертывания на Timeweb Cloud

## Этап 1: Подготовка проекта (локально)

### Шаг 11ние архива проекта1. Откройте папку с проектом
2. Выделите все файлы (Ctrl+A)
3. Создайте ZIP архив (правый клик → Отправить" → Сжатая папка")4. Назовите архив `accounting_project.zip`

### Шаг 1.2: Обновление requirements.txt
Добавьте в файл `requirements.txt` следующие строки:
```
PyMySQL==1.1.0
gunicorn==21.2.0
```

### Шаг10.3: Создание файла .env
Создайте файл `.env` в корне проекта:
```
# Настройки базы данных (заполните позже)
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

## Этап2: Создание сервера на Timeweb Cloud

### Шаг 2.1Регистрация и вход
1йдите на сайт timeweb.cloud
2. Зарегистрируйтесь или войдите в аккаунт
3. Перейдите в разделОблачные серверы"

### Шаг2.2 Создание виртуального сервера
1. Нажмите Создать сервер"2Выберите конфигурацию:
   - **ОС**: Ubuntu220.04 LTS
   - **RAM**:2 GB (минимум)
   - **CPU**:1 ядро (минимум)
   - **Диск**: 20GB (минимум)
3 Выберите регион (ближайший к вам)
4. Нажмите "Создать"
5. Дождитесь создания сервера (510 минут)

### Шаг 2.3: Получение данных для подключения
1. В панели управления найдите ваш сервер2 Запишите:
   - **IP адрес сервера** (например:1230.4560.7890.123)
   - **Логин** (обычно `root`)
   - **Пароль** (указан при создании)

## Этап 3: Подключение к серверу

### Шаг 3.1 Установка SSH клиента (если нет)
**Для Windows:**
1. Скачайте и установите PuTTY: https://www.putty.org/
2 Или используйте встроенный SSH в Windows 101

**Для Mac/Linux:**
SSH уже установлен

### Шаг 3.2 Подключение к серверу
**Через PuTTY (Windows):**
1. Откройте PuTTY
2. В поле "Host Nameвведите IP сервера
3 Порт: 224. НажмитеOpen5. Введите логин: `root`6. Введите пароль (при вводе символы не отображаются)

**Через терминал (Mac/Linux):**
```bash
ssh root@IP_АДРЕС_СЕРВЕРА
```

## Этап 4 Настройка сервера

### Шаг 4.1: Обновление системы
```bash
apt update && apt upgrade -y
```

### Шаг 4.2: Установка необходимого ПО
```bash
# Установка Python и pip
apt install python3 python3pip python3-venv -y

# Установка Nginx (веб-сервер)
apt install nginx -y

# Установка Supervisor (управление процессами)
apt install supervisor -y

# Установка MySQL клиента
apt install mysql-client -y
```

### Шаг 4.3: Создание пользователя для приложения
```bash
# Создание пользователя
adduser webapp

# Добавление в группу sudo
usermod -aG sudo webapp

# Переключение на пользователя webapp
su - webapp
```

## Этап 5: Загрузка проекта на сервер

### Шаг50.1Создание папки для проекта
```bash
# Убедитесь, что вы пользователь webapp
whoami

# Создание папки
mkdir ~/accounting_app
cd ~/accounting_app
```

### Шаг52: Загрузка файлов
**Вариант A: Через SCP (рекомендуется)**1 Откройте новое окно терминала на вашем компьютере
2 Перейдите в папку с архивом проекта
3 Выполните команду:
```bash
scp accounting_project.zip webapp@IP_АДРЕС_СЕРВЕРА:~/accounting_app/
```

**Вариант B: Через веб-интерфейс**
1. В панели Timeweb Cloud найдите ваш сервер
2 Нажмите Файловый менеджер"
3 Загрузите архив в папку `/home/webapp/accounting_app/`

### Шаг 5.3: Распаковка проекта
```bash
# Вернитесь в терминал сервера
cd ~/accounting_app

# Распаковка архива
unzip accounting_project.zip

# Удаление архива
rm accounting_project.zip
```

## Этап 6: Настройка Python окружения

### Шаг6.1 Создание виртуального окружения
```bash
# Создание виртуального окружения
python3 -m venv venv

# Активация виртуального окружения
source venv/bin/activate

# Проверка активации (должен показать путь к venv)
which python
```

### Шаг 6.2: Установка зависимостей
```bash
# Обновление pip
pip install --upgrade pip

# Установка зависимостей
pip install -r requirements.txt
```

## Этап7тройка базы данных

### Шаг 7.1здание базы данных в Timeweb Cloud
1. В панели Timeweb Cloud перейдите в раздел Базы данных"2 Создайте новую базу данных MySQL:
   - **Название**: `accounting_system`
   - **Пользователь**: создайте нового пользователя
   - **Пароль**: придумайте надежный пароль
3шите данные подключения:
   - **Хост**: (указан в панели)
   - **Порт**: 3306
   - **База данных**: `accounting_system`
   - **Пользователь**: (созданный пользователь)
   - **Пароль**: (указанный пароль)

### Шаг 7.2 Создание таблиц в базе данных
1. В панели Timeweb Cloud найдите вашу базу данных2ажмите phpMyAdminили Веб-консоль
3. Войдите с данными пользователя базы данных
4. Выберите базу данных `accounting_system`5Перейдите на вкладку SQL
6. Выполните SQL команды для создания таблиц (см. ниже)

### Шаг 7.3: SQL для создания таблиц
Скопируйте и выполните следующий SQL код:

```sql
-- Таблица сотрудников
CREATE TABLE employee (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100NULL,
    telegram VARCHAR(10,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    salary_percent FLOAT
);

-- Таблица аккаунтов
CREATE TABLE account (
    id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT,
    platform VARCHAR(20) NOT NULL,
    account_name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (employee_id) REFERENCES employee(id)
);

-- Таблица отчетов о сменах
CREATE TABLE shift_report (
    id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT NOT NULL,
    shift_date DATE NOT NULL,
    shift_type VARCHAR(20) NOT NULL,
    department VARCHAR(20) NOT NULL DEFAULT first,  shift_start_date DATE,
    shift_end_date DATE,
    total_requests INT DEFAULT 0,
    balances_json TEXT NOT NULL DEFAULT '{},   scam_amount DECIMAL(15,2) DEFAULT 0
    scam_amount_rub DECIMAL(15,2) DEFAULT 0,
    scam_platform VARCHAR(20 DEFAULTbybit,
    scam_account VARCHAR(100FAULT '',
    scam_comment TEXT DEFAULT 
    scam_count_in_sales BOOLEAN DEFAULT FALSE,
    scam_count_in_purchases BOOLEAN DEFAULT FALSE,
    dokidka_amount DECIMAL(15,2) DEFAULT 0,
    dokidka_amount_rub DECIMAL(15,2) DEFAULT 0,
    dokidka_platform VARCHAR(20 DEFAULT bybit',
    dokidka_account VARCHAR(100EFAULT '',
    dokidka_count_in_sales BOOLEAN DEFAULT FALSE,
    dokidka_count_in_purchases BOOLEAN DEFAULT FALSE,
    internal_transfer_amount DECIMAL(15,2) DEFAULT 0,
    internal_transfer_amount_rub DECIMAL(15,2) DEFAULT 0,
    internal_transfer_platform VARCHAR(20 DEFAULT 'bybit',
    internal_transfer_account VARCHAR(100T '',
    internal_transfer_count_in_sales BOOLEAN DEFAULT FALSE,
    internal_transfer_count_in_purchases BOOLEAN DEFAULT FALSE,
    dokidka_comment TEXT DEFAULT '',
    internal_transfer_comment TEXT DEFAULT bybit_file VARCHAR(255    bybit_btc_file VARCHAR(255  htx_file VARCHAR(255bliss_file VARCHAR(255),
    start_photo VARCHAR(255 end_photo VARCHAR(255    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    bybit_requests INT DEFAULT 0,
    htx_requests INT DEFAULT 0,
    bliss_requests INT DEFAULT 0
    bybit_first_trade VARCHAR(100DEFAULT ,
    bybit_last_trade VARCHAR(100 DEFAULT,   htx_first_trade VARCHAR(100 DEFAULT     htx_last_trade VARCHAR(100AULT ',
    bliss_first_trade VARCHAR(100AULT ,
    bliss_last_trade VARCHAR(100FAULT ,
    gate_first_trade VARCHAR(100FAULT,   gate_last_trade VARCHAR(100ULT '',
    appeal_amount DECIMAL(15,2) DEFAULT 0,
    appeal_amount_rub DECIMAL(15,2) DEFAULT 0,
    appeal_platform VARCHAR(20 DEFAULT 'bybit',
    appeal_account VARCHAR(100ULT '',
    appeal_comment TEXT DEFAULT '',
    appeal_deducted BOOLEAN DEFAULT FALSE,
    appeal_count_in_sales BOOLEAN DEFAULT FALSE,
    appeal_count_in_purchases BOOLEAN DEFAULT FALSE,
    shift_start_time DATETIME,
    shift_end_time DATETIME,
    FOREIGN KEY (employee_id) REFERENCES employee(id)
);

-- Таблица деталей ордеров
CREATE TABLE order_detail (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shift_report_id INT NOT NULL,
    order_id VARCHAR(100T NULL,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    quantity DECIMAL(15OT NULL,
    price DECIMAL(15OT NULL,
    total_usdt DECIMAL(15NOT NULL,
    fees_usdt DECIMAL(15,2) DEFAULT 0,
    status VARCHAR(20) NOT NULL,
    executed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shift_report_id) REFERENCES shift_report(id)
);

-- Таблица начальных балансов
CREATE TABLE initial_balance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    platform VARCHAR(20) NOT NULL,
    account_name VARCHAR(100 NULL,
    balance DECIMAL(15,2) NOT NULL DEFAULT 0
);

-- Таблица истории балансов аккаунтов
CREATE TABLE account_balance_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    account_id INT,
    account_name VARCHAR(100NULL,
    platform VARCHAR(20) NOT NULL,
    shift_date DATE NOT NULL,
    shift_type VARCHAR(20) NOT NULL,
    balance DECIMAL(15NULL,
    employee_id INT,
    employee_name VARCHAR(100),
    balance_type VARCHAR(10) NOT NULL DEFAULT end,
    FOREIGN KEY (account_id) REFERENCES account(id),
    FOREIGN KEY (employee_id) REFERENCES employee(id)
);

-- Таблица ордеров
CREATE TABLE `order` (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id VARCHAR(100 NOT NULL UNIQUE,
    employee_id INT NOT NULL,
    platform VARCHAR(20) NOT NULL DEFAULT 'bybit',
    account_name VARCHAR(100T NULL,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    quantity DECIMAL(15OT NULL,
    price DECIMAL(15OT NULL,
    total_usdt DECIMAL(15NOT NULL,
    fees_usdt DECIMAL(15,2) DEFAULT 0,
    status VARCHAR(20) NOT NULL,
    count_in_sales BOOLEAN DEFAULT FALSE,
    count_in_purchases BOOLEAN DEFAULT FALSE,
    executed_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employee(id)
);

-- Таблица истории скамов сотрудников
CREATE TABLE employee_scam_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT NOT NULL,
    shift_report_id INT NOT NULL,
    amount DECIMAL(15 NULL,
    comment TEXT DEFAULT
    date DATE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employee(id),
    FOREIGN KEY (shift_report_id) REFERENCES shift_report(id)
);

-- Таблица настроек зарплаты
CREATE TABLE salary_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    base_percent INT NOT NULL DEFAULT30
    min_daily_profit FLOAT NOT NULL DEFAULT 100
    bonus_percent INT NOT NULL DEFAULT 5,
    bonus_profit_threshold FLOAT NOT NULL DEFAULT 1500    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

## Этап 8астройка конфигурации приложения

### Шаг80.1Создание файла конфигурации
```bash
# Убедитесь, что вы в папке проекта
cd ~/accounting_app

# Создание файла конфигурации
nano config.py
```

### Шаг 80.2: Содержимое файла config.py
Скопируйте в файл:

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
    # Замените на ваши данные базы данных
    SQLALCHEMY_DATABASE_URI =mysql+pymysql://ВАШ_ПОЛЬЗОВАТЕЛЬ:ВАШ_ПАРОЛЬ@ВАШ_ХОСТ:3306/accounting_system'

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///arbitrage_reports.db'

config = [object Object]development': DevelopmentConfig,production': ProductionConfig,
    'default': DevelopmentConfig
}
```

### Шаг 80.3 Обновление app.py
```bash
# Откройте файл app.py для редактирования
nano app.py
```

Найдите строку:
```python
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///arbitrage_reports.db')
```

Замените на:
```python
from config import config
import os

# Выбор конфигурации
config_name = os.environ.get('FLASK_ENV',production)
app.config.from_object(config[config_name])
```

## Этап 9 Настройка Nginx

### Шаг90.1Создание конфигурации Nginx
```bash
# Создание конфигурации
sudo nano /etc/nginx/sites-available/accounting_app
```

### Шаг 90.2: Содержимое конфигурации Nginx
Скопируйте в файл:

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

### Шаг 93ктивация конфигурации
```bash
# Создание символической ссылки
sudo ln -s /etc/nginx/sites-available/accounting_app /etc/nginx/sites-enabled/

# Удаление дефолтной конфигурации
sudo rm /etc/nginx/sites-enabled/default

# Проверка конфигурации
sudo nginx -t

# Перезапуск Nginx
sudo systemctl reload nginx
```

## Этап 10: Настройка Supervisor

### Шаг 100.1Создание конфигурации Supervisor
```bash
# Создание конфигурации
sudo nano /etc/supervisor/conf.d/accounting_app.conf
```

### Шаг 100.2: Содержимое конфигурации Supervisor
Скопируйте в файл:

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

### Шаг 100.3оздание директории для логов
```bash
# Создание директории
sudo mkdir -p /var/log/accounting_app

# Изменение владельца
sudo chown webapp:webapp /var/log/accounting_app
```

### Шаг 10.4: Запуск приложения
```bash
# Перезапуск Supervisor
sudo supervisorctl reread
sudo supervisorctl update

# Запуск приложения
sudo supervisorctl start accounting_app

# Проверка статуса
sudo supervisorctl status accounting_app
```

## Этап 11 Проверка работы

### Шаг 11.1Проверка логов
```bash
# Проверка логов приложения
tail -f /var/log/accounting_app/out.log

# Проверка логов ошибок
tail -f /var/log/accounting_app/err.log
```

### Шаг 110.2: Проверка в браузере
1. Откройте браузер
2. Введите IP адрес вашего сервера
3. Должна открыться страница приложения

### Шаг 113: Проверка портов
```bash
# Проверка, что приложение слушает порт 800tstat -tlnp | grep :8000
# Проверка, что Nginx слушает порт 80tstat -tlnp | grep :80``

## Этап12: Настройка домена (опционально)

### Шаг12.1: Покупка домена1те домен (например, на reg.ru)
2. Настройте DNS записи:
   - Тип: A
   - Имя: @
   - Значение: IP адрес вашего сервера

### Шаг 120.2: Обновление конфигурации Nginx
```bash
# Редактирование конфигурации
sudo nano /etc/nginx/sites-available/accounting_app
```

Замените строку:
```nginx
server_name IP_АДРЕС_СЕРВЕРА;
```

На:
```nginx
server_name ваш-домен.ru www.ваш-домен.ru;
```

### Шаг 12.3: Перезапуск Nginx
```bash
sudo systemctl reload nginx
```

## Этап13 Настройка SSL (опционально)

### Шаг 130.1 Установка Certbot
```bash
sudo apt install certbot python3-certbot-nginx -y
```

### Шаг 13.2 Получение SSL сертификата
```bash
sudo certbot --nginx -d ваш-домен.ru
```

## Этап 14ервное копирование

### Шаг140.1: Создание скрипта резервного копирования
```bash
# Создание скрипта
nano ~/backup.sh
```

### Шаг 142: Содержимое скрипта резервного копирования
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=~/backups

mkdir -p $BACKUP_DIR

# Резервное копирование базы данных
mysqldump -h ВАШ_ХОСТ -u ВАШ_ПОЛЬЗОВАТЕЛЬ -pВАШ_ПАРОЛЬ accounting_system > $BACKUP_DIR/db_backup_$DATE.sql

# Резервное копирование файлов
tar -czf $BACKUP_DIR/files_backup_$DATE.tar.gz ~/accounting_app/uploads

echo "Резервное копирование завершено: $DATE
```

### Шаг 14.3: Настройка автоматического резервного копирования
```bash
# Права на выполнение
chmod +x ~/backup.sh

# Добавление в cron (ежедневно в2)
crontab -e
```

Добавьте строку:
```
0 * * * ~/backup.sh
```

## Этап 15: Мониторинг и обслуживание

### Шаг 150.1: Проверка статуса сервисов
```bash
# Статус приложения
sudo supervisorctl status accounting_app

# Статус Nginx
sudo systemctl status nginx

# Статус MySQL
sudo systemctl status mysql
```

### Шаг 150.2овление приложения
```bash
# Остановка приложения
sudo supervisorctl stop accounting_app

# Обновление кода (если используете git)
cd ~/accounting_app
git pull origin main

# Обновление зависимостей
source venv/bin/activate
pip install -r requirements.txt

# Запуск приложения
sudo supervisorctl start accounting_app
```

## 🎉 Готово!

Ваше приложение теперь работает на Timeweb Cloud!

### Полезные команды:
- **Проверка логов**: `tail -f /var/log/accounting_app/out.log`
- **Перезапуск приложения**: `sudo supervisorctl restart accounting_app`
- **Перезапуск Nginx**: `sudo systemctl reload nginx`
- **Проверка статуса**: `sudo supervisorctl status accounting_app`

### Если что-то не работает:
1Проверьте логи: `/var/log/accounting_app/err.log`
2. Проверьте подключение к базе данных
3роверьте конфигурацию Nginx: `sudo nginx -t`
4Проверьте права доступа к файлам

### Контакты для поддержки:
- Timeweb Cloud поддержка
- Документация Flask
- Документация Nginx 