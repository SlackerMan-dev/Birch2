#!/usr/bin/env python3
"крипт для экспорта данных из SQLite в формат для импорта в MySQL
ort sqlite3
import json
import os
from datetime import datetime

def export_sqlite_data():
 кспортирует данные из SQLite в JSON файлы
    
    # Подключение к SQLite базе данных
    sqlite_db = arbitrage_reports.db'
    if not os.path.exists(sqlite_db):
        print(f"❌ Файл базы данных {sqlite_db} не найден!")
        return False
    
    conn = sqlite3.connect(sqlite_db)
    cursor = conn.cursor()
    
    # Список таблиц для экспорта
    tables = [
  employee',
  account,   shift_report',
      order_detail',
      initial_balance',
      account_balance_history',
        order
    employee_scam_history,  salary_settings'
    ]
    
    exported_data = {}
    
    for table in tables:
        try:
            # Получаем структуру таблицы
            cursor.execute(fPRAGMA table_info({table})")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            # Получаем данные
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            
            # Преобразуем в список словарей
            table_data =            for row in rows:
                row_dict = [object Object]               for i, value in enumerate(row):
                    # Обработка специальных типов данных
                    if isinstance(value, datetime):
                        value = value.isoformat()
                    elif value is None:
                        value = None
                    row_dict[column_names[i]] = value
                table_data.append(row_dict)
            
            exported_data[table] =[object Object]
               columns': column_names,
                data': table_data
            }
            
            print(f"✅ Экспортировано {len(table_data)} записей из таблицы {table}")
            
        except Exception as e:
            print(f❌ Ошибка при экспорте таблицы {table}: {e}")
            continue
    
    # Сохраняем данные в JSON файл
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S)
    export_file = f'sqlite_export_{timestamp}.json'
    
    with open(export_file, w, encoding='utf-8as f:
        json.dump(exported_data, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n✅ Данные экспортированы в файл: {export_file}")
    print(f📊 Всего экспортировано таблиц: {len(exported_data)}")
    
    # Выводим статистику
    total_records = sum(len(table_info[data]) for table_info in exported_data.values())
    print(f📈 Всего записей: {total_records}")
    
    conn.close()
    return true

def create_mysql_schema():
   Создает SQL скрипт для создания таблиц в MySQL"
    
    schema_sql = """
-- Создание таблиц для MySQL
-- Кодировка: utf8mb4

-- Таблица сотрудников
CREATE TABLE IF NOT EXISTS employee (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100NULL,
    telegram VARCHAR(10,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    salary_percent FLOAT
);

-- Таблица аккаунтов
CREATE TABLE IF NOT EXISTS account (
    id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT,
    platform VARCHAR(20) NOT NULL,
    account_name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (employee_id) REFERENCES employee(id)
);

-- Таблица отчетов о сменах
CREATE TABLE IF NOT EXISTS shift_report (
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
CREATE TABLE IF NOT EXISTS order_detail (
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
CREATE TABLE IF NOT EXISTS initial_balance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    platform VARCHAR(20) NOT NULL,
    account_name VARCHAR(100 NULL,
    balance DECIMAL(15,2) NOT NULL DEFAULT 0
);

-- Таблица истории балансов аккаунтов
CREATE TABLE IF NOT EXISTS account_balance_history (
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
CREATE TABLE IF NOT EXISTS `order` (
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
CREATE TABLE IF NOT EXISTS employee_scam_history (
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
CREATE TABLE IF NOT EXISTS salary_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    base_percent INT NOT NULL DEFAULT30
    min_daily_profit FLOAT NOT NULL DEFAULT 100
    bonus_percent INT NOT NULL DEFAULT 5,
    bonus_profit_threshold FLOAT NOT NULL DEFAULT 1500    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Индексы для оптимизации
CREATE INDEX idx_employee_name ON employee(name);
CREATE INDEX idx_account_platform ON account(platform);
CREATE INDEX idx_shift_report_employee ON shift_report(employee_id);
CREATE INDEX idx_shift_report_date ON shift_report(shift_date);
CREATE INDEX idx_order_employee ON `order`(employee_id);
CREATE INDEX idx_order_executed_at ON `order`(executed_at);
CREATE INDEX idx_order_platform ON `order`(platform);    
    # Сохраняем схему в файл
    with open('mysql_schema.sql,w, encoding='utf-8) asf:
        f.write(schema_sql)
    
    print("✅ Схема MySQL создана в файле: mysql_schema.sql)
    return True

if __name__ == "__main__":
    print("🚀 Начинаем экспорт данных из SQLite...")
    
    # Создаем схему MySQL
    create_mysql_schema()
    
    # Экспортируем данные
    if export_sqlite_data():
        print("\n🎉 Экспорт завершен успешно!")
        print(undefinedn📋 Следующие шаги:)
        print(1. Загрузите файл mysql_schema.sql в MySQL для создания таблиц)
        print(2. Используйте скрипт import_mysql_data.py для импорта данных)
        print(3.Обновите конфигурацию приложения для работы с MySQL")
    else:
        print(undefinedn❌ Экспорт завершился с ошибками!") 