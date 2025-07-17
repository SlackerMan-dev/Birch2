-- Создание таблиц для MySQL
-- Кодировка: utf8mb4

-- Таблица сотрудников
CREATE TABLE IF NOT EXISTS employee (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NULL,
    telegram VARCHAR(10) NULL,
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
    department VARCHAR(20) NOT NULL DEFAULT 'first',
    shift_start_date DATE,
    shift_end_date DATE,
    total_requests INT DEFAULT 0,
    balances_json TEXT NOT NULL,
    scam_amount DECIMAL(15,2) DEFAULT 0,
    scam_amount_rub DECIMAL(15,2) DEFAULT 0,
    scam_platform VARCHAR(20) DEFAULT 'bybit',
    scam_account VARCHAR(100) DEFAULT '',
    scam_comment TEXT,
    scam_count_in_sales BOOLEAN DEFAULT FALSE,
    scam_count_in_purchases BOOLEAN DEFAULT FALSE,
    dokidka_amount DECIMAL(15,2) DEFAULT 0,
    dokidka_amount_rub DECIMAL(15,2) DEFAULT 0,
    dokidka_platform VARCHAR(20) DEFAULT 'bybit',
    dokidka_account VARCHAR(100) DEFAULT '',
    dokidka_count_in_sales BOOLEAN DEFAULT FALSE,
    dokidka_count_in_purchases BOOLEAN DEFAULT FALSE,
    internal_transfer_amount DECIMAL(15,2) DEFAULT 0,
    internal_transfer_amount_rub DECIMAL(15,2) DEFAULT 0,
    internal_transfer_platform VARCHAR(20) DEFAULT 'bybit',
    internal_transfer_account VARCHAR(100) DEFAULT '',
    internal_transfer_count_in_sales BOOLEAN DEFAULT FALSE,
    internal_transfer_count_in_purchases BOOLEAN DEFAULT FALSE,
    dokidka_comment TEXT,
    internal_transfer_comment TEXT,
    bybit_file VARCHAR(255) NULL,
    bybit_btc_file VARCHAR(255) NULL,
    htx_file VARCHAR(255) NULL,
    bliss_file VARCHAR(255) NULL,
    start_photo VARCHAR(255) NULL,
    end_photo VARCHAR(255) NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    bybit_requests INT DEFAULT 0,
    htx_requests INT DEFAULT 0,
    bliss_requests INT DEFAULT 0,
    bybit_first_trade VARCHAR(100) DEFAULT '',
    bybit_last_trade VARCHAR(100) DEFAULT '',
    htx_first_trade VARCHAR(100) DEFAULT '',
    htx_last_trade VARCHAR(100) DEFAULT '',
    bliss_first_trade VARCHAR(100) DEFAULT '',
    bliss_last_trade VARCHAR(100) DEFAULT '',
    gate_first_trade VARCHAR(100) DEFAULT '',
    gate_last_trade VARCHAR(100) DEFAULT '',
    appeal_amount DECIMAL(15,2) DEFAULT 0,
    appeal_amount_rub DECIMAL(15,2) DEFAULT 0,
    appeal_platform VARCHAR(20) DEFAULT 'bybit',
    appeal_account VARCHAR(100) DEFAULT '',
    appeal_comment TEXT,
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
    order_id VARCHAR(100) NULL,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    quantity DECIMAL(15,2) NULL,
    price DECIMAL(15,2) NULL,
    total_usdt DECIMAL(15,2) NOT NULL,
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
    account_name VARCHAR(100) NULL,
    balance DECIMAL(15,2) NOT NULL DEFAULT 0
);

-- Таблица истории балансов аккаунтов
CREATE TABLE IF NOT EXISTS account_balance_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    account_id INT,
    account_name VARCHAR(100) NULL,
    platform VARCHAR(20) NOT NULL,
    shift_date DATE NOT NULL,
    shift_type VARCHAR(20) NOT NULL,
    balance DECIMAL(15,2) NULL,
    employee_id INT,
    employee_name VARCHAR(100),
    balance_type VARCHAR(10) NOT NULL DEFAULT 'end',
    FOREIGN KEY (account_id) REFERENCES account(id),
    FOREIGN KEY (employee_id) REFERENCES employee(id)
);

-- Таблица ордеров
CREATE TABLE IF NOT EXISTS `order` (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id VARCHAR(100) NOT NULL UNIQUE,
    employee_id INT NOT NULL,
    platform VARCHAR(20) NOT NULL DEFAULT 'bybit',
    account_name VARCHAR(100) NULL,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    quantity DECIMAL(15,2) NULL,
    price DECIMAL(15,2) NULL,
    total_usdt DECIMAL(15,2) NOT NULL,
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
    amount DECIMAL(15,2) NULL,
    comment TEXT,
    date DATE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employee(id),
    FOREIGN KEY (shift_report_id) REFERENCES shift_report(id)
);

-- Таблица настроек зарплаты
CREATE TABLE IF NOT EXISTS salary_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    base_percent INT NOT NULL DEFAULT 30,
    min_daily_profit FLOAT NOT NULL DEFAULT 100,
    bonus_percent INT NOT NULL DEFAULT 5,
    bonus_profit_threshold FLOAT NOT NULL DEFAULT 1500,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Индексы создаются отдельно в файле mysql_indexes.sql 