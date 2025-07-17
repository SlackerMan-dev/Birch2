-- Создание индексов для оптимизации
-- Выполните этот файл отдельно после создания таблиц

-- Проверка и создание индексов для таблицы employee
SELECT IF(
    (SELECT COUNT(*) FROM information_schema.statistics 
     WHERE table_schema = DATABASE() 
     AND table_name = 'employee' 
     AND index_name = idx_employee_name') = 0,
    CREATEINDEX idx_employee_name ON employee(name)',
    SELECT "Index idx_employee_name already exists"
) INTO @sql;
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Проверка и создание индексов для таблицы account
SELECT IF(
    (SELECT COUNT(*) FROM information_schema.statistics 
     WHERE table_schema = DATABASE() 
     AND table_name = 'account' 
     AND index_name = 'idx_account_platform') = 0,
   CREATE INDEX idx_account_platform ON account(platform)',
    SELECTIndex idx_account_platform already exists"
) INTO @sql;
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Проверка и создание индексов для таблицы shift_report
SELECT IF(
    (SELECT COUNT(*) FROM information_schema.statistics 
     WHERE table_schema = DATABASE() 
     AND table_name = 'shift_report' 
     AND index_name = idx_shift_report_employee') = 0,
    CREATE INDEX idx_shift_report_employee ON shift_report(employee_id)',
    SELECT "Index idx_shift_report_employee already exists"
) INTO @sql;
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT IF(
    (SELECT COUNT(*) FROM information_schema.statistics 
     WHERE table_schema = DATABASE() 
     AND table_name = 'shift_report' 
     AND index_name =idx_shift_report_date') = 0,
    CREATE INDEX idx_shift_report_date ON shift_report(shift_date)',
    SELECT "Index idx_shift_report_date already exists"
) INTO @sql;
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Проверка и создание индексов для таблицы order
SELECT IF(
    (SELECT COUNT(*) FROM information_schema.statistics 
     WHERE table_schema = DATABASE() 
     AND table_name =order' 
     AND index_name = 'idx_order_employee') = 0,
   CREATE INDEX idx_order_employee ON `order`(employee_id)',
    SELECTIndexidx_order_employee already exists"
) INTO @sql;
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT IF(
    (SELECT COUNT(*) FROM information_schema.statistics 
     WHERE table_schema = DATABASE() 
     AND table_name =order' 
     AND index_name = 'idx_order_executed_at') = 0,
   CREATE INDEX idx_order_executed_at ON `order`(executed_at)',
    SELECT "Index idx_order_executed_at already exists"
) INTO @sql;
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT IF(
    (SELECT COUNT(*) FROM information_schema.statistics 
     WHERE table_schema = DATABASE() 
     AND table_name =order' 
     AND index_name = 'idx_order_platform') = 0,
   CREATE INDEX idx_order_platform ON `order`(platform)',
    SELECTIndexidx_order_platform already exists"
) INTO @sql;
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT 'All indexes created successfully!' AS result; 