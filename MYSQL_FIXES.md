# 🔧 Исправления для MySQL

## Проблема: MySQL не поддерживает DEFAULT для TEXT полей

### ❌ Ошибка:
```
#1101 - Невозможно указывать значение по умолчанию для столбца BLOB 'balances_json'
```

### ✅ Решение:
Удалены значения по умолчанию для всех полей типа `TEXT`:

**Было:**
```sql
balances_json TEXT NOT NULL DEFAULT {}
scam_comment TEXT DEFAULT ',
dokidka_comment TEXT DEFAULT 
internal_transfer_comment TEXT DEFAULT ppeal_comment TEXT DEFAULT '',
comment TEXT DEFAULT,
```

**Стало:**
```sql
balances_json TEXT NOT NULL,
scam_comment TEXT,
dokidka_comment TEXT,
internal_transfer_comment TEXT,
appeal_comment TEXT,
comment TEXT,
```

## 📋 Обновленный SQL код

Теперь используйте исправленный файл `mysql_schema.sql` - все проблемы с TEXT полями решены!

## 🔄 Как применить исправления:

1**В phpMyAdmin:**
   - Выберите вашу базу данных
   - Перейдите на вкладку "SQL"
   - Выполните содержимое файла `mysql_schema.sql`
2 **Через командную строку:**
   ```bash
   mysql -u your_username -p your_database < mysql_schema.sql
   ```

## ⚠️ Важные замечания:

1. **TEXT поля будут пустыми** по умолчанию - это нормально
2. **Приложение само заполнит** эти поля при необходимости
3. **Если нужно значение по умолчанию** - используйте `VARCHAR` вместо `TEXT`

## 🎉 Готово!

Теперь SQL код должен выполняться без ошибок в MySQL! 