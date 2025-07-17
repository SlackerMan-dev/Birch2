#!/usr/bin/env python3
"""
Скрипт для запуска сервера Flask с проверкой работоспособности
"""
import os
import sys
import subprocess
import time
import requests
from threading import Thread

def check_server_status():
    """Проверяет статус сервера"""
    try:
        response = requests.get('http://localhost:5000/api/employees', timeout=5)
        if response.status_code == 200:
            print("✅ Сервер работает корректно!")
            employees = response.json()
            print(f"   Найдено сотрудников: {len(employees)}")
            return True
        else:
            print(f"❌ Сервер отвечает с ошибкой: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Сервер недоступен")
        return False
    except Exception as e:
        print(f"❌ Ошибка проверки сервера: {e}")
        return False

def start_server():
    """Запускает сервер Flask"""
    try:
        print("🚀 Запускаем сервер Flask...")
        
        # Проверяем наличие app.py
        if not os.path.exists('app.py'):
            print("❌ Файл app.py не найден!")
            return False
        
        # Запускаем сервер
        process = subprocess.Popen([
            sys.executable, 'app.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        print("⏳ Ждем запуска сервера...")
        time.sleep(3)
        
        # Проверяем статус
        if process.poll() is None:  # Процесс еще работает
            print("✅ Сервер запущен!")
            
            # Проверяем доступность API
            if check_server_status():
                print("\n🎉 Сервер готов к работе!")
                print("📝 Теперь можно тестировать расширение Bybit")
                print("🔗 Адрес сервера: http://localhost:5000")
                return True
            else:
                print("❌ Сервер запущен, но API недоступен")
                process.terminate()
                return False
        else:
            print("❌ Не удалось запустить сервер")
            stdout, stderr = process.communicate()
            if stderr:
                print(f"Ошибка: {stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка запуска сервера: {e}")
        return False

def check_dependencies():
    """Проверяет необходимые зависимости"""
    print("🔍 Проверяем зависимости...")
    
    required_packages = ['pandas', 'openpyxl', 'flask', 'flask_sqlalchemy', 'flask_cors']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - НЕ УСТАНОВЛЕН")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n📦 Для загрузки файлов установите недостающие пакеты:")
        print(f"pip install {' '.join(missing_packages)}")
        print("или:")
        print("pip install -r requirements.txt")
        return False
    
    print("✅ Все зависимости установлены!")
    return True

def main():
    print("🔧 Проверка и запуск сервера")
    print("=" * 50)
    
    # Проверяем зависимости
    check_dependencies()
    print()
    
    # Сначала проверяем, не запущен ли уже сервер
    print("🔍 Проверяем, не запущен ли уже сервер...")
    if check_server_status():
        print("✅ Сервер уже работает!")
        return
    
    # Запускаем сервер
    if start_server():
        print("\n💡 Инструкции:")
        print("1. Откройте систему в браузере: http://localhost:5000")
        print("2. Перейдите на вкладку 'История ордеров'")
        print("3. Нажмите 'Загрузить выгрузку' для загрузки файлов")
        print("4. Или используйте расширение браузера для автоматического отслеживания")
        print("5. Для тестирования запустите: python test_upload.py")
        
        # Ждем завершения работы
        try:
            input("\nНажмите Enter для остановки сервера...")
        except KeyboardInterrupt:
            pass
        
        print("\n🛑 Остановка сервера...")
    else:
        print("❌ Не удалось запустить сервер")

if __name__ == "__main__":
    main() 