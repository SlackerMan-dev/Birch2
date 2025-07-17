# Birch2 Flask Application

Веб-приложение для управления отчетами и данными торговых платформ.

## Описание

Это Flask-приложение для:
- Управления сотрудниками и аккаунтами
- Обработки отчетов смен
- Анализа торговых данных с платформ (Bybit, HTX, Bliss, Gate)
- Расчета зарплат и статистики

## Технологии

- **Backend**: Flask, SQLAlchemy
- **База данных**: MySQL
- **Frontend**: HTML, CSS, JavaScript
- **Деплой**: Timeweb Cloud

## Установка и запуск

### Локальная разработка

1. Клонируйте репозиторий:
```bash
git clone <your-repo-url>
cd birch2-flask-app
```

2. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Настройте переменные окружения:
```bash
export FLASK_CONFIG=development
export DATABASE_URL=sqlite:///arbitrage_reports.db
```

5. Запустите приложение:
```bash
python app.py
```

### Продакшн деплой

1. Настройте переменные окружения:
```bash
export FLASK_CONFIG=production
export DB_HOST=your-mysql-host
export DB_NAME=your-database-name
export DB_USER=your-username
export DB_PASS=your-password
```

2. Запустите с Gunicorn:
```bash
gunicorn app:app
```

## Структура проекта

```
birch2-flask-app/
├── app.py              # Основное Flask приложение
├── config.py           # Конфигурация
├── utils.py            # Вспомогательные функции
├── requirements.txt    # Зависимости Python
├── .gitignore         # Исключения для Git
├── README.md          # Документация
└── uploads/           # Папка для загруженных файлов
```

## API Endpoints

- `GET /` - Главная страница
- `GET /api/employees` - Список сотрудников
- `POST /api/employees` - Создание сотрудника
- `GET /api/reports` - Список отчетов
- `POST /api/reports` - Создание отчета
- `GET /api/dashboard` - Данные дашборда

## Лицензия

Private project 