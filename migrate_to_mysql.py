#!/usr/bin/env python3
Скрипт для миграции данных из SQLite в MySQL
ort sqlite3
import pymysql
import os
from datetime import datetime

def migrate_sqlite_to_mysql():
    "игрирует данные из SQLite в MySQL"
    
    # Проверяем наличие SQLite файла
    sqlite_db = arbitrage_reports.db'
    if not os.path.exists(sqlite_db):
        print(f❌ Файл {sqlite_db} не найден!")
        return False
    
    # Данные подключения к MySQL (замените на ваши)
    mysql_config =[object Object]
        host': 'localhost,
    user':your_username',
       password':your_password',
   database': accounting_system',
        charset': 'utf8mb4'
    }
    
    print("🔍 Подключение к базам данных...")
    
    try:
        # Подключение к SQLite
        sqlite_conn = sqlite3.connect(sqlite_db)
        sqlite_cursor = sqlite_conn.cursor()
        
        # Подключение к MySQL
        mysql_conn = pymysql.connect(**mysql_config)
        mysql_cursor = mysql_conn.cursor()
        
        print("✅ Подключение успешно!")
        
        # Список таблиц для миграции
        tables = [
      employee',
      account', 
          shift_report',
          order_detail',
          initial_balance',
          account_balance_history',
   order',
        employee_scam_history',
            salary_settings'
        ]
        
        for table in tables:
            try:
                print(f"\n📊 Миграция таблицы: {table}")
                
                # Получаем данные из SQLite
                sqlite_cursor.execute(f"SELECT * FROM {table})              rows = sqlite_cursor.fetchall()
                
                if not rows:
                    print(f"   ⚠️  Таблица {table} пуста")
                    continue
                
                # Получаем структуру таблицы
                sqlite_cursor.execute(fPRAGMA table_info({table}))           columns = sqlite_cursor.fetchall()
                column_names = [col[1] for col in columns]
                
                # Подготавливаем SQL для вставки
                placeholders = , .join([%s* len(column_names))
                columns_str = , .join([f'`{col}`' for col in column_names])
                
                insert_sql = f"INSERT INTO `{table}` ({columns_str}) VALUES ({placeholders})"
                
                # Вставляем данные в MySQL
                for row in rows:
                    # Обработка специальных типов данных
                    processed_row = []
                    for i, value in enumerate(row):
                        if isinstance(value, datetime):
                            value = value.isoformat()
                        elif value is None:
                            value = None
                        processed_row.append(value)
                    
                    mysql_cursor.execute(insert_sql, processed_row)
                
                mysql_conn.commit()
                print(f"   ✅ Мигрировано[object Object]len(rows)} записей")
                
            except Exception as e:
                print(f"   ❌ Ошибка при миграции таблицы {table}: {e})          continue
        
        print("\n🎉 Миграция завершена!")
        
        # Закрываем соединения
        sqlite_conn.close()
        mysql_conn.close()
        
        returntrue       
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False

def create_mysql_tables():
    Создает таблицы в MySQL 
    mysql_config =[object Object]
        host': 'localhost,
    user':your_username',
       password':your_password',
   database': accounting_system',
        charset': 'utf8mb4'
    }
    
    try:
        # Подключение к MySQL
        mysql_conn = pymysql.connect(**mysql_config)
        mysql_cursor = mysql_conn.cursor()
        
        # Читаем SQL файл
        with open('mysql_schema.sql,r, encoding='utf-8') as f:
            sql_content = f.read()
        
        # Выполняем SQL команды
        for statement in sql_content.split(';'):
            statement = statement.strip()
            if statement:
                mysql_cursor.execute(statement)
        
        mysql_conn.commit()
        mysql_conn.close()
        
        print(✅ Таблицы созданы успешно!")
        returntrue       
    except Exception as e:
        print(f❌ Ошибка создания таблиц: {e}")
        return False

if __name__ == "__main__":
    print(🚀 Начинаем миграцию данных...")
    
    # Создаем таблицы
    if create_mysql_tables():
        # Мигрируем данные
        if migrate_sqlite_to_mysql():
            print("\n🎉 Миграция завершена успешно!")
            print(📋Следующие шаги:")
            print(1.Обновите конфигурацию приложения для работы с MySQL")
            print("2. Протестируйте приложение")
            print(3.Удалите старый SQLite файл после проверки")
        else:
            print("\n❌ Миграция данных завершилась с ошибками!")
    else:
        print("\n❌ Создание таблиц завершилось с ошибками!") 