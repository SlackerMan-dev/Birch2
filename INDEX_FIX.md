# 🔧 Решение проблемы с дублирующимися индексами

## Проблема:
```
#1061 Дублирующееся имя ключа 'idx_order_executed_at'
```

## Причина:
Индекс уже существует в таблице, возможно, от предыдущего выполнения SQL.

## ✅ Решение:

### Вариант 1алить существующие индексы (если они есть)
```sql
-- Удалите существующие индексы, если они есть
DROP INDEX IF EXISTS idx_employee_name ON employee;
DROP INDEX IF EXISTS idx_account_platform ON account;
DROP INDEX IF EXISTS idx_shift_report_employee ON shift_report;
DROP INDEX IF EXISTS idx_shift_report_date ON shift_report;
DROP INDEX IF EXISTS idx_order_employee ON `order`;
DROP INDEX IF EXISTS idx_order_executed_at ON `order`;
DROP INDEX IF EXISTS idx_order_platform ON `order`;
```

### Вариант 2: Использовать отдельный файл для индексов
1. Сначала выполните `mysql_schema.sql` (без индексов)
2 Затем выполните `mysql_indexes.sql` (только индексы)

### Вариант 3 Создать индексы вручную
```sql
-- Создайте индексы по одному, пропуская существующие
CREATE INDEX idx_employee_name ON employee(name);
CREATE INDEX idx_account_platform ON account(platform);
CREATE INDEX idx_shift_report_employee ON shift_report(employee_id);
CREATE INDEX idx_shift_report_date ON shift_report(shift_date);
CREATE INDEX idx_order_employee ON `order`(employee_id);
CREATE INDEX idx_order_executed_at ON `order`(executed_at);
CREATE INDEX idx_order_platform ON `order`(platform);
```

## 📋 Пошаговый план:

1. **Выполните основной SQL** (`mysql_schema.sql`) - создаст таблицы
2. **Проверьте существующие индексы:**
   ```sql
   SHOW INDEX FROM employee;
   SHOW INDEX FROM account;
   SHOW INDEX FROM shift_report;
   SHOW INDEX FROM `order`;
   ```
3. **Удалите существующие индексы** (если есть)
4. **Создайте индексы заново**

## 🎉 Альтернатива:
Индексы не критичны для работы приложения - можно пропустить их создание и добавить позже при необходимости оптимизации.

## ⚠️ Важно:
- Индексы улучшают производительность запросов
- Но приложение будет работать и без них
- Можно создать индексы позже через phpMyAdmin 