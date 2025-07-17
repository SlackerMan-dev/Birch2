# 🚀 Быстрый старт: Развертывание на Timeweb Cloud

## Шаг1: Создание сервера
1Зайдите на timeweb.cloud
2. Создайте виртуальный сервер:
   - ОС: Ubuntu 22.4LTS
   - RAM: 2 GB
   - CPU: 1ядро
   - Диск:20 GB3 Запишите IP адрес сервера

## Шаг 2: Подключение к серверу
```bash
ssh root@IP_АДРЕС_СЕРВЕРА
```

## Шаг3 Автоматическая настройка сервера
```bash
# Скачайте и запустите скрипт настройки
wget https://raw.githubusercontent.com/your-repo/setup_server.sh
chmod +x setup_server.sh
./setup_server.sh
```

## Шаг 4: Загрузка проекта
```bash
# Переключитесь на пользователя webapp
su - webapp

# Создайте архив проекта локально и загрузите на сервер
# Затем распакуйте в /home/webapp/accounting_app/
```

## Шаг 5: Настройка Python окружения
```bash
cd ~/accounting_app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Шаг6тройка базы данных
1. В панели Timeweb Cloud создайте MySQL базу данных
2шите данные подключения3Обновите конфигурацию в файле config.py

## Шаг 7: Запуск приложения
```bash
sudo supervisorctl start accounting_app
```

## Шаг 8 Проверка
Откройте в браузере: http://IP_АДРЕС_СЕРВЕРА

## Полезные команды:
- Проверка статуса: `sudo supervisorctl status accounting_app`
- Просмотр логов: `tail -f /var/log/accounting_app/out.log`
- Перезапуск: `sudo supervisorctl restart accounting_app` 