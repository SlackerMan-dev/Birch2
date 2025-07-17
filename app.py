from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
import json
from decimal import Decimal
import os
from werkzeug.utils import secure_filename
from sqlalchemy import func, text
from utils import (
    find_prev_balance,
    calculate_profit_from_orders,
    calculate_report_profit,
    calculate_account_last_balance,
    group_reports_by_day_net_profit
)
import re
from config import config

# Опциональный импорт pandas
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None

app = Flask(__name__)

# Определяем конфигурацию в зависимости от окружения
config_name = os.environ.get('FLASK_CONFIG', 'production')
app.config.from_object(config[config_name])

db = SQLAlchemy(app)
CORS(app)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls', 'png', 'jpg', 'jpeg', 'webp', 'pdf', 'txt'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_file_size(file):
    """Дополнительная проверка размера файла"""
    if file and hasattr(file, 'content_length') and file.content_length:
        return file.content_length <= app.config['MAX_CONTENT_LENGTH']
    return True

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# --- КОНСТАНТЫ И ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
PLATFORMS = ['bybit', 'htx', 'bliss', 'gate']
ADMIN_PASSWORD = 'Blalala2'

def validate_admin_password(data):
    """Проверяет пароль администратора"""
    if not data or not data.get('password'):
        return False
    # Используем переменную окружения для пароля администратора
    admin_password = os.environ.get('ADMIN_PASSWORD', 'Blalala2')
    return data['password'] == admin_password

def convert_to_moscow_time(datetime_obj, platform):
    """
    Конвертирует время из часового пояса платформы в московское время
    
    Args:
        datetime_obj: объект datetime
        platform: название платформы ('bybit', 'htx', 'bliss')
    
    Returns:
        datetime объект в московском времени
    """
    if not datetime_obj:
        print(f"DEBUG TIMEZONE: Получен пустой datetime_obj для {platform}")
        return datetime_obj
    
    # Определяем смещение для каждой платформы относительно Москвы
    timezone_offsets = {
        'bybit': 3,   # Bybit время в UTC+0, МСК это UTC+3 → добавляем 3 часа
        'htx': -5,    # HTX время в UTC+8, МСК это UTC+3 → вычитаем 5 часов
        'bliss': 3,   # Bliss время в UTC+0, МСК это UTC+3 → добавляем 3 часа
        'gate': 0     # Gate.io: пока без смещения (можно настроить позже)
    }
    
    offset_hours = timezone_offsets.get(platform.lower(), 0)
    
    # Применяем смещение
    if offset_hours != 0:
        print(f"DEBUG TIMEZONE: Конвертируем {datetime_obj} для {platform}")
        print(f"DEBUG TIMEZONE: Смещение {offset_hours} часов")
        datetime_obj = datetime_obj + timedelta(hours=offset_hours)
        print(f"DEBUG TIMEZONE: Результат -> {datetime_obj}")
    else:
        print(f"DEBUG TIMEZONE: Нет смещения для платформы {platform}")
    
    return datetime_obj

def parse_orders_file(filepath, platform, start_date=None, end_date=None, original_filename=None):
    """Парсит файл с ордерами в зависимости от платформы"""
    try:
        # Проверяем, что файл существует
        if not os.path.exists(filepath):
            print(f"Ошибка: файл {filepath} не существует")
            return []
        
        # Определяем тип файла по расширению
        ext = os.path.splitext(filepath)[1].lower()
        
        if platform.lower() == 'bliss':
            try:
                # Пробуем разные разделители
                separators = [';', ',', '\t']
                df = None
                
                print(f"\nBLISS DEBUG: Пытаемся прочитать файл {filepath}")
                print(f"BLISS DEBUG: Размер файла: {os.path.getsize(filepath)} байт")
                
                # Читаем первые несколько строк файла для отладки
                with open(filepath, 'r', encoding='utf-8') as f:
                    print("BLISS DEBUG: Первые строки файла:")
                    for i, line in enumerate(f):
                        if i < 5:  # Показываем первые 5 строк
                            print(f"BLISS DEBUG: Строка {i+1}: {line.strip()}")
                
                for sep in separators:
                    try:
                        print(f"\nBLISS DEBUG: Пробуем разделитель '{sep}'")
                        print(f"BLISS DEBUG: Путь к файлу: {filepath}")
                        
                        # Читаем первые несколько строк для отладки
                        with open(filepath, 'r', encoding='utf-8') as f:
                            print("BLISS DEBUG: Первые 3 строки файла:")
                            for i, line in enumerate(f):
                                if i < 3:
                                    print(f"BLISS DEBUG: {line.strip()}")
                        
                        df = pd.read_csv(filepath, sep=sep, encoding='utf-8', quotechar='"', header=0)
                        print(f"BLISS DEBUG: Успешно прочитали файл")
                        print(f"BLISS DEBUG: Найдены колонки: {list(df.columns)}")
                        print(f"BLISS DEBUG: Количество строк: {len(df)}")
                        
                        # Проверяем, что нашли нужные колонки
                        required_columns = ['Creation date', 'Internal id', 'Organization user', 'Amount', 'Crypto amount', 'Status', 'Method']
                        missing_columns = [col for col in required_columns if col not in df.columns]
                        
                        if missing_columns:
                            print(f"BLISS DEBUG: Отсутствуют колонки: {missing_columns}")
                            continue
                        else:
                            print(f"BLISS DEBUG: Успешно прочитали файл с разделителем '{sep}'")
                            break
                    except Exception as e:
                        print(f"BLISS DEBUG: Не удалось прочитать файл с разделителем '{sep}': {str(e)}")
                        continue
                
                if df is None:
                    print("BLISS DEBUG: Не удалось прочитать файл ни с одним разделителем")
                    return []
                
                orders_data = []
                for _, row in df.iterrows():
                    try:
                        # Получаем необходимые поля
                        order_id = str(row['Internal id']).strip()
                        account_name = str(row['Organization user']).strip()
                        amount = str(row['Amount']).strip().replace(' ', '').replace(',', '.')
                        crypto_amount = str(row['Crypto amount']).strip().replace(' ', '').replace(',', '.')
                        status = str(row['Status']).strip()
                        method = str(row['Method']).strip()  # Добавляем поле Method
                        
                        print(f"\nBLISS DEBUG: Обрабатываем строку:")
                        print(f"BLISS DEBUG: order_id = {order_id}")
                        print(f"BLISS DEBUG: account_name = {account_name}")
                        print(f"BLISS DEBUG: amount = {amount}")
                        print(f"BLISS DEBUG: crypto_amount = {crypto_amount}")
                        print(f"BLISS DEBUG: status = {status}")
                        print(f"BLISS DEBUG: method = {method}")
                        
                        # Определяем сторону ордера на основе метода
                        if method.lower() in ['sell', 'продажа', 'продать']:
                            side = 'sell'
                        else:
                            side = 'buy'
                        
                        # Получаем время создания
                        creation_date = str(row['Creation date']).strip()
                        if creation_date:
                            try:
                                print(f"BLISS DEBUG: Исходная строка даты: '{creation_date}'")
                                executed_at = datetime.strptime(creation_date, '%d.%m.%Y %H:%M:%S')
                                print(f"BLISS DEBUG: Распарсенная дата: {executed_at}")
                                
                                # Конвертируем время в московское
                                executed_at = convert_to_moscow_time(executed_at, platform)
                                print(f"BLISS DEBUG: Дата в МСК: {executed_at}")
                                
                                # Фильтруем по времени, если указаны границы
                                if start_date and executed_at < start_date:
                                    print(f"BLISS DEBUG: Ордер {order_id} раньше начальной даты")
                                    continue
                                if end_date and executed_at > end_date:
                                    print(f"BLISS DEBUG: Ордер {order_id} позже конечной даты")
                                    continue
                                
                            except Exception as e:
                                print(f"BLISS DEBUG: Ошибка обработки даты: '{creation_date}', ошибка: {str(e)}")
                                executed_at = datetime.now()
                        else:
                            print(f"BLISS DEBUG: Пустая дата в строке")
                            executed_at = datetime.now()
                        
                        # Конвертируем числовые значения
                        try:
                            total_usdt = float(amount)
                            quantity = float(crypto_amount)
                            print(f"BLISS DEBUG: total_usdt = {total_usdt}, quantity = {quantity}")
                        except:
                            print(f"BLISS DEBUG: Ошибка конвертации чисел: amount={amount}, crypto_amount={crypto_amount}")
                            continue
                        
                        # Проверяем обязательные поля
                        if not order_id:
                            print(f"BLISS DEBUG: Пропускаем строку - не найден ID ордера")
                            continue
                        
                        if not account_name:
                            print(f"BLISS DEBUG: Пропускаем строку - не найдено имя аккаунта")
                            continue
                        
                        # Вычисляем цену
                        price = total_usdt / quantity if quantity > 0 else 0
                        print(f"BLISS DEBUG: Вычисленная цена: {price}")
                        
                        # Определяем статус
                        if status.lower() in ['success', 'completed', 'done']:
                            order_status = 'filled'
                        elif status.lower() in ['cancelled', 'canceled']:
                            order_status = 'canceled'
                        elif status.lower() in ['expired']:
                            order_status = 'expired'
                        elif status.lower() in ['failed']:
                            order_status = 'failed'
                        else:
                            order_status = 'pending'
                        
                        order_data = {
                            'order_id': order_id,
                            'symbol': 'USDT',
                            'side': side,
                            'quantity': quantity,
                            'price': price,
                            'total_usdt': total_usdt,
                            'fees_usdt': 0,
                            'status': order_status,
                            'executed_at': executed_at
                        }
                        
                        print(f"BLISS DEBUG: Создан order_data:")
                        for key, value in order_data.items():
                            print(f"BLISS DEBUG: {key} = {value}")
                        
                        orders_data.append(order_data)
                        print(f"BLISS DEBUG: Ордер {order_id} добавлен в список")
                        
                    except Exception as e:
                        print(f"BLISS DEBUG: Ошибка парсинга строки: {str(e)}")
                        continue
                
                print(f"BLISS DEBUG: Всего обработано {len(orders_data)} ордеров")
                return orders_data
                
            except Exception as e:
                print(f"BLISS: Ошибка чтения файла: {str(e)}")
                return []
                
        elif ext in ['.csv']:
            df = pd.read_csv(filepath)
        elif ext in ['.xlsx', '.xls']:
            df = pd.read_excel(filepath)
        else:
            raise Exception(f"Неподдерживаемый формат файла: {ext}")
        
        orders_data = []
        
        if platform.lower() == 'bybit':
            # Парсинг файла Bybit
            for _, row in df.iterrows():
                try:
                    # Извлекаем данные из строки
                    order_data = parse_bybit_order(row)
                    if order_data:
                        # Конвертируем время в московское
                        order_data['executed_at'] = convert_to_moscow_time(order_data['executed_at'], 'bybit')
                        
                        # Фильтруем по времени, если указаны границы
                        if start_date or end_date:
                            order_time = order_data['executed_at']
                            
                            # Проверяем начальную дату
                            if start_date and order_time < start_date:
                                continue
                            
                            # Проверяем конечную дату
                            if end_date and order_time > end_date:
                                continue
                        
                        orders_data.append(order_data)
                except Exception as e:
                    print(f"Ошибка парсинга ордера Bybit: {str(e)}")
                    continue
        elif platform.lower() == 'bybit_btc':
            # Парсинг BTC файла Bybit (CSV с данными в первом столбце)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Пропускаем заголовок
                for line in lines[1:]:
                    try:
                        # Парсим строку BTC файла
                        order_data = parse_bybit_btc_csv_line(line)
                        if order_data:
                            # Конвертируем время в московское (+3 часа)
                            order_data['executed_at'] = convert_to_moscow_time(order_data['executed_at'], 'bybit')
                            
                            # Фильтруем по времени, если указаны границы
                            if start_date or end_date:
                                order_time = order_data['executed_at']
                                
                                # Проверяем начальную дату
                                if start_date and order_time < start_date:
                                    continue
                                
                                # Проверяем конечную дату
                                if end_date and order_time > end_date:
                                    continue
                            
                            orders_data.append(order_data)
                    except Exception as e:
                        print(f"Ошибка парсинга BTC строки: {str(e)}")
                        continue
                        
            except Exception as e:
                print(f"Ошибка чтения BTC файла: {str(e)}")
                return []
                
        elif platform.lower() == 'htx':
            # Парсинг файла HTX
            for _, row in df.iterrows():
                try:
                    # Извлекаем данные из строки
                    order_data = parse_htx_order(row)
                    if order_data:
                        # Конвертируем время в московское
                        order_data['executed_at'] = convert_to_moscow_time(order_data['executed_at'], platform)
                        
                        # Фильтруем по времени, если указаны границы
                        if start_date or end_date:
                            order_time = order_data['executed_at']
                            
                            # Проверяем начальную дату
                            if start_date and order_time < start_date:
                                continue
                            
                            # Проверяем конечную дату
                            if end_date and order_time > end_date:
                                continue
                        
                        orders_data.append(order_data)
                except Exception as e:
                    print(f"Ошибка парсинга ордера HTX: {str(e)}")
                    continue
                
        elif platform.lower() == 'gate':
            # Парсинг файла Gate
            for _, row in df.iterrows():
                try:
                    # Извлекаем данные из строки
                    order_data = parse_gate_order(row)
                    if order_data:
                        # Конвертируем время в московское
                        order_data['executed_at'] = convert_to_moscow_time(order_data['executed_at'], platform)
                        
                        # Фильтруем по времени, если указаны границы
                        if start_date or end_date:
                            order_time = order_data['executed_at']
                            
                            # Проверяем начальную дату
                            if start_date and order_time < start_date:
                                continue
                            
                            # Проверяем конечную дату
                            if end_date and order_time > end_date:
                                continue
                        
                        orders_data.append(order_data)
                except Exception as e:
                    print(f"Ошибка парсинга ордера Gate: {str(e)}")
                    continue
        
        return orders_data
        
    except Exception as e:
        print(f"Ошибка парсинга файла: {str(e)}")
        return []

def parse_bybit_btc_csv_line(line):
    """Парсит строку из BTC CSV файла Bybit (разделяет по запятой, все строки попадают в таблицу, пустые поля заменяются на числовые значения или None)"""
    try:
        # Разделяем строку по запятой
        parts = line.strip().split(',')
        # Гарантируем, что parts всегда длины 14
        while len(parts) < 14:
            parts.append('')
        
        currency = parts[0].strip() if parts[0].strip() else ''
        contract = parts[1].strip() if parts[1].strip() else ''
        transaction_type = parts[2].strip() if parts[2].strip() else ''
        direction = parts[3].strip() if parts[3].strip() else ''
        quantity = parts[4].strip() if parts[4].strip() else ''
        position = parts[5].strip() if parts[5].strip() else ''
        filled_price = parts[6].strip() if parts[6].strip() else ''
        funding = parts[7].strip() if parts[7].strip() else ''
        fee_paid = parts[8].strip() if parts[8].strip() else ''
        cash_flow = parts[9].strip() if parts[9].strip() else ''
        change = parts[10].strip() if parts[10].strip() else ''
        wallet_balance = parts[11].strip() if parts[11].strip() else ''
        action = parts[12].strip() if parts[12].strip() else ''
        time_str = parts[13].strip() if parts[13].strip() else ''

        # Символ (Contract - Пара)
        symbol = contract if contract else (currency if currency else 'USDT')
        # Сторона
        side = direction if direction else '--'
        # Количество (USDT) - числовое значение или 0
        try:
            quantity_val = float(quantity) if quantity and quantity not in ('', None) else 0.0
        except Exception:
            quantity_val = 0.0
        # Цена - числовое значение или 0
        try:
            price_val = float(filled_price) if filled_price and filled_price not in ('', None) else 0.0
        except Exception:
            price_val = 0.0
        # Дата
        if not time_str or time_str == '':
            executed_at = datetime.now()
        else:
            try:
                executed_at = datetime.strptime(time_str, '%d.%m.%Y %H:%M')
            except Exception:
                try:
                    executed_at = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                except Exception:
                    executed_at = datetime.now()
        # order_id основан на содержимом строки для предотвращения дубликатов
        # Используем более стабильный хеш от ключевых полей
        import hashlib
        key_fields = f"{currency}_{contract}_{direction}_{quantity}_{filled_price}_{time_str}"
        # Создаем MD5 хеш для стабильности
        hash_object = hashlib.md5(key_fields.encode('utf-8'))
        order_id = f"btc_{hash_object.hexdigest()[:16]}"
        return {
            'order_id': order_id,
            'symbol': symbol,
            'side': side,
            'quantity': quantity_val,
            'price': price_val,
            'total_usdt': 0.0,  # Для BTC ордеров всегда 0
            'fees_usdt': 0.0,   # Для BTC ордеров всегда 0
            'status': 'Завершен',
            'executed_at': executed_at
        }
    except Exception as e:
        print(f"Ошибка парсинга BTC строки: {e}")
        return None

def parse_bybit_order(row):
    """Парсит строку ордера Bybit"""
    try:
        # Ищем нужные столбцы в строке
        order_id = None
        symbol = None
        side = None
        coin_amount = None  # Объем (USDT) - из Coin Amount
        price = None        # Цена - из Price
        fiat_amount = None  # Объем (RUB) - из Fiat Amount
        status = 'filled'   # Статус по умолчанию
        executed_at = None
        
        # Проверяем разные варианты названий столбцов
        for col in row.index:
            col_lower = str(col).lower().strip()
            col_value = str(row[col]).strip()
            
            # Order ID - различные варианты
            if any(x in col_lower for x in ['order no', 'order id', 'orderid', 'order_id', 'номер']):
                order_id = col_value
            
            # Symbol/Pair - торговая пара (из Cryptocurrency)
            elif any(x in col_lower for x in ['cryptocurrency', 'symbol', 'pair', 'пара', 'инструмент', 'currency', 'валюта']):
                if col_value and col_value.lower() not in ['nan', 'none', '']:
                    symbol = col_value.upper()  # Приводим к верхнему регистру
            
            # Side/Type - направление сделки
            elif any(x in col_lower for x in ['side', 'type', 'тип', 'направление']):
                side_value = col_value.lower()
                if any(x in side_value for x in ['buy', 'покупка', 'long']):
                    side = 'buy'
                elif any(x in side_value for x in ['sell', 'продажа', 'short']):
                    side = 'sell'
            
            # Coin Amount - количество криптовалюты (идет в колонку Объем USDT)
            elif any(x in col_lower for x in ['coin amount', 'coinamount', 'coin_amount']):
                try:
                    clean_value = re.sub(r'[^\d.,]', '', col_value)
                    if clean_value:
                        coin_amount = float(clean_value.replace(',', '.'))
                except:
                    pass
            
            # Price - цена (идет в колонку Цена)
            elif any(x in col_lower for x in ['price', 'цена', 'курс']):
                try:
                    clean_value = re.sub(r'[^\d.,]', '', col_value)
                    if clean_value:
                        price = float(clean_value.replace(',', '.'))
                except:
                    pass
            
            # Fiat Amount - сумма в фиатной валюте (идет в колонку Объем RUB)
            elif any(x in col_lower for x in ['fiat amount', 'fiatamount', 'fiat_amount']):
                try:
                    clean_value = re.sub(r'[^\d.,]', '', col_value)
                    if clean_value:
                        fiat_amount = float(clean_value.replace(',', '.'))
                except:
                    pass
            
            # Status - статус
            elif any(x in col_lower for x in ['status', 'статус']):
                if col_value and col_value.lower() not in ['nan', 'none', '']:
                    status = col_value.lower()
                    if 'completed' in status or 'завершен' in status:
                        status = 'filled'
                    elif 'canceled' in status or 'отменен' in status:
                        status = 'canceled'
                    elif 'pending' in status or 'ожидание' in status:
                        status = 'pending'
                    elif 'Оформление жалоб' in status or 'оформление жалоб' in status:
                        status = 'appealed'  # Новый статус - как апелляция
                    else:
                        status = 'filled'  # По умолчанию
            
            # Time - время
            elif any(x in col_lower for x in ['time', 'date', 'время', 'дата', 'created']):
                try:
                    if col_value and col_value != 'nan':
                        if PANDAS_AVAILABLE:
                            executed_at = pd.to_datetime(col_value)
                        else:
                            # Простой парсинг даты без pandas
                            executed_at = datetime.strptime(col_value, '%Y-%m-%d %H:%M:%S')
                except:
                    pass
        
        # Попытка автоматически вычислить недостающие значения
        # Вычисляем price, если есть coin_amount и fiat_amount
        if price is None and coin_amount not in [None, 0] and fiat_amount not in [None, 0]:
            try:
                price = fiat_amount / coin_amount if coin_amount else None
            except Exception as _:
                pass
        # Вычисляем fiat_amount, если есть price и coin_amount
        if fiat_amount is None and price not in [None, 0] and coin_amount not in [None, 0]:
            try:
                fiat_amount = price * coin_amount
            except Exception as _:
                pass

        # Установка значения по умолчанию для symbol
        if not symbol or str(symbol).lower() in ['nan', 'none', '']:
            symbol = 'USDT'

        # Проверяем, что все необходимые данные есть после попыток вычисления
        if not order_id or coin_amount is None or (price is None and fiat_amount is None):
            print(f"Пропускаем строку - недостаточно данных: order_id={order_id}, coin_amount={coin_amount}, price={price}, fiat_amount={fiat_amount}")
            return None
        
        # Дополнительная проверка на корректность symbol
        if symbol.lower() in ['nan', 'none', '']:
            print(f"Пропускаем строку - некорректный символ: {symbol}")
            return None
        
        # Если нет времени, используем текущее
        if not executed_at:
            executed_at = datetime.now()
        
        return {
            'order_id': order_id,
            'symbol': symbol,
            'side': side,
            'quantity': coin_amount,    # Объем (USDT) - из Coin Amount
            'price': price,            # Цена - из Price
            'total_usdt': fiat_amount, # Объем (RUB) - из Fiat Amount
            'fees_usdt': 0,
            'status': status,          # Статус - из Status
            'executed_at': executed_at
        }
        
    except Exception as e:
        print(f"Ошибка парсинга ордера Bybit: {e}")
        return None

def parse_htx_order(row):
    """Парсит строку ордера HTX с учетом специфики формата HTX"""
    try:
        # Инициализируем переменные
        order_id = None
        symbol = None
        side = None
        quantity = None     # Объем (USDT) - из Количество
        price = None        # Цена - из Цена за ед.
        total_usdt = None   # Объем (RUB) - из Общая цена
        status = 'filled'   # Статус по умолчанию
        executed_at = None
        
        # Прямой маппинг колонок HTX
        for col in row.index:
            col_str = str(col).strip()
            col_value = str(row[col]).strip()
            
            # Order ID - Номер:
            if col_str == 'Номер:':
                order_id = col_value
            
            # Symbol/Pair - Монета (USDT + RUB = USDT)
            elif col_str == 'Монета':
                if col_value and col_value.lower() not in ['nan', 'none', '']:
                    symbol = col_value.upper()  # USDT
            
            # Side/Type - Тип (Продать/Купить)
            elif col_str == 'Тип':
                if 'Продать' in col_value or 'продать' in col_value:
                    side = 'sell'
                elif 'Купить' in col_value or 'купить' in col_value:
                    side = 'buy'
            
            # Quantity - Количество
            elif col_str == 'Количество':
                try:
                    if col_value and col_value != 'nan':
                        quantity = float(col_value.replace(',', '.'))
                except:
                    pass
            
            # Price - Цена за ед.
            elif col_str == 'Цена за ед.':
                try:
                    if col_value and col_value != 'nan':
                        price = float(col_value.replace(',', '.'))
                except:
                    pass
            
            # Total - Общая цена
            elif col_str == 'Общая цена':
                try:
                    if col_value and col_value != 'nan':
                        total_usdt = float(col_value.replace(',', '.'))
                except:
                    pass
            
            # Status - Статус
            elif col_str == 'Статус':
                if col_value and col_value.lower() not in ['nan', 'none', '']:
                    if 'Завершено' in col_value or 'завершено' in col_value:
                        status = 'filled'
                    elif 'Отменено' in col_value or 'отменено' in col_value:
                        status = 'canceled'
                    elif 'Ожидание' in col_value or 'ожидание' in col_value:
                        status = 'pending'
                    elif 'Оформление жалоб' in col_value or 'оформление жалоб' in col_value:
                        status = 'appealed'  # Новый статус - как апелляция
                    else:
                        status = 'filled'  # По умолчанию
            
            # Time - Время
            elif col_str == 'Время':
                try:
                    if col_value and col_value != 'nan':
                        if PANDAS_AVAILABLE:
                            executed_at = pd.to_datetime(col_value)
                        else:
                            # Простой парсинг даты без pandas
                            executed_at = datetime.strptime(col_value, '%Y-%m-%d %H:%M:%S')
                except:
                    pass
        
        # Попытка автоматически вычислить недостающие значения
        if price is None and quantity not in [None, 0] and total_usdt not in [None, 0]:
            try:
                price = total_usdt / quantity if quantity else None
            except Exception:
                pass
        if total_usdt is None and price not in [None, 0] and quantity not in [None, 0]:
            try:
                total_usdt = price * quantity
            except Exception:
                pass

        # Устанавливаем значение символа по умолчанию, если не удалось прочитать
        if not symbol or str(symbol).lower() in ['nan', 'none', '']:
            symbol = 'USDT'

        # Проверяем, что все необходимые данные есть после вычислений
        if not order_id or quantity is None or (price is None and total_usdt is None):
            print(f"HTX: Пропускаем строку - недостаточно данных: order_id={order_id}, quantity={quantity}, price={price}, total_usdt={total_usdt}")
            return None
        
        # Дополнительная проверка на корректность symbol
        if symbol.lower() in ['nan', 'none', '']:
            print(f"HTX: Пропускаем строку - некорректный символ: {symbol}")
            return None
        
        # Если нет времени, используем текущее
        if not executed_at:
            executed_at = datetime.now()
        
        return {
            'order_id': order_id,
            'symbol': symbol,
            'side': side,
            'quantity': quantity,      # Объем (USDT) - из Количество
            'price': price,           # Цена - из Цена за ед.
            'total_usdt': total_usdt, # Объем (RUB) - из Общая цена
            'fees_usdt': 0,
            'status': status,         # Статус - из Статус
            'executed_at': executed_at
        }
        
    except Exception as e:
        print(f"Ошибка парсинга ордера HTX: {e}")
        return None

def parse_gate_order(row):
    """Парсит строку ордера Gate.io"""
    # Аналогично Bybit, но с учетом специфики Gate
    return parse_bybit_order(row)  # Пока используем тот же парсер

def parse_bliss_order(row):
    """Парсит строку ордера Bliss с учетом специфики формата Bliss"""
    try:
        # Инициализируем переменные
        order_id = None
        symbol = 'USDT'  # Всегда USDT для Bliss
        side = 'buy'     # Всегда покупка согласно описанию
        quantity = None  # Объем (USDT) - из Crypto amount
        price = None     # Цена - пропускается поле
        total_usdt = None  # Объем (RUB) - из Amount
        status = 'filled'  # Статус по умолчанию
        executed_at = None
        
        # Отладка: выводим все колонки
        print(f"BLISS DEBUG: Все колонки в строке: {list(row.index)}")
        
        for col in row.index:
            col_str = str(col).strip()
            col_value = str(row[col]).strip()
            
            print(f"BLISS DEBUG: Обрабатываем колонку '{col_str}' со значением '{col_value}'")
            
            # Order ID - Internal id
            if col_str == 'Internal id':
                order_id = col_value
                print(f"BLISS DEBUG: Найден order_id: {order_id}")
            
            # Quantity - Crypto amount
            elif col_str == 'Crypto amount':
                try:
                    if col_value and col_value != 'nan':
                        # Убираем запятые и конвертируем в float
                        quantity = float(col_value.replace(',', '.'))
                        print(f"BLISS DEBUG: Найден quantity: {quantity}")
                except:
                    pass
            
            # Total USDT - Amount
            elif col_str == 'Amount':
                try:
                    if col_value and col_value != 'nan':
                        # Убираем запятые и конвертируем в float
                        total_usdt = float(col_value.replace(',', '.'))
                        print(f"BLISS DEBUG: Найден total_usdt: {total_usdt}")
                except:
                    pass
            
            # Status - Status
            elif col_str == 'Status':
                if col_value and col_value != 'nan':
                    status_value = col_value.lower()
                    if status_value in ['success', 'completed', 'done']:
                        status = 'filled'
                    elif status_value in ['cancelled', 'canceled']:
                        status = 'canceled'
                    elif status_value in ['expired']:
                        status = 'expired'
                    elif status_value in ['failed']:
                        status = 'failed'
                    else:
                        status = 'pending'
                    print(f"BLISS DEBUG: Найден status: {status}")
            
            # Time - пробуем разные варианты названий колонок с датой
            elif col_str in ['Finish date', 'Creation date', 'Date', 'Time', 'Timestamp', 'Дата завершения', 'Время']:
                print(f"BLISS DEBUG: Найдена колонка с датой '{col_str}' со значением '{col_value}'")
                try:
                    if col_value and col_value != 'nan':
                        # Пробуем разные форматы даты
                        date_formats = [
                            '%d.%m.%Y %H:%M',
                            '%d.%m.%Y %H:%M:%S',
                            '%Y-%m-%d %H:%M:%S',
                            '%Y-%m-%d %H:%M',
                            '%d/%m/%Y %H:%M',
                            '%d-%m-%Y %H:%M'
                        ]
                        
                        for date_format in date_formats:
                            try:
                                if PANDAS_AVAILABLE:
                                    executed_at = pd.to_datetime(col_value, format=date_format)
                                else:
                                    executed_at = datetime.strptime(col_value, date_format)
                                print(f"BLISS DEBUG: Успешно распарсили дату '{col_value}' в формате '{date_format}' -> {executed_at}")
                                break
                            except:
                                continue
                        else:
                            print(f"BLISS DEBUG: Не удалось распарсить дату '{col_value}' ни в одном формате")
                except Exception as e:
                    print(f"BLISS DEBUG: Ошибка парсинга даты '{col_value}': {e}")
        
        # Вычисляем цену на основе имеющихся данных
        price = None
        if quantity is not None and total_usdt is not None and quantity > 0:
            price = total_usdt / quantity
        
        # Проверяем, что все необходимые данные есть
        if not order_id or quantity is None or total_usdt is None or price is None:
            print(f"BLISS: Пропускаем строку - недостаточно данных: order_id={order_id}, symbol={symbol}, side={side}, quantity={quantity}, price={price}, total_usdt={total_usdt}")
            return None
        
        # Если нет времени, используем текущее
        if not executed_at:
            executed_at = datetime.now()
        
        # Время будет конвертировано позже в process_platform_file
        # executed_at остаётся в исходном часовом поясе
        
        return {
            'order_id': order_id,
            'account_name': None,  # Не используем имя аккаунта из файла
            'symbol': symbol,
            'side': side,              # Всегда 'buy'
            'quantity': quantity,      # Объем (USDT) - из Crypto amount
            'price': price,            # Цена - вычисляется
            'total_usdt': total_usdt,  # Объем (RUB) - из Amount
            'fees_usdt': 0,
            'status': status,          # Статус - из Status
            'executed_at': executed_at
        }
        
    except Exception as e:
        print(f"BLISS: Ошибка парсинга строки: {str(e)}")
        return None

# Модели данных
class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    telegram = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    salary_percent = db.Column(db.Float, nullable=True)  # Новый процент для расчёта зарплаты

class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=True)
    platform = db.Column(db.String(20), nullable=False)  # bybit, htx, bliss, gate
    account_name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

class ShiftReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    shift_date = db.Column(db.Date, nullable=False)
    shift_type = db.Column(db.String(20), nullable=False)  # 'morning' или 'evening'
    department = db.Column(db.String(20), nullable=False, default='first')  # 'first' или 'second' - отдел
    # Новые поля для диапазона дат
    shift_start_date = db.Column(db.Date, nullable=True)  # Дата начала диапазона
    shift_end_date = db.Column(db.Date, nullable=True)    # Дата окончания диапазона
    total_requests = db.Column(db.Integer, default=0)  # всего заявок обработано
    # Балансы по аккаунтам (json: {"bybit": [{"account_id": 1, "balance": 123.45}, ...], ...})
    balances_json = db.Column(db.Text, nullable=False, default='{}')
    # СКАМ
    scam_amount = db.Column(db.Numeric(15, 2), default=0)
    scam_amount_rub = db.Column(db.Numeric(15, 2), default=0)  # Сумма скама в рублях
    scam_platform = db.Column(db.String(20), default='bybit')  # Платформа для скама
    scam_account = db.Column(db.String(100), default='')  # Аккаунт для скама
    scam_comment = db.Column(db.Text, default='')

    scam_count_in_sales = db.Column(db.Boolean, default=False)  # Учитывать в продажах
    scam_count_in_purchases = db.Column(db.Boolean, default=False)  # Учитывать в покупках
    # ПЕРЕВОДЫ
    dokidka_amount = db.Column(db.Numeric(15, 2), default=0)  # Новое поле: докидка (внешний перевод)
    dokidka_amount_rub = db.Column(db.Numeric(15, 2), default=0)  # Сумма докидки в рублях
    dokidka_platform = db.Column(db.String(20), default='bybit')  # Платформа для докидки
    dokidka_account = db.Column(db.String(100), default='')  # Аккаунт для докидки
    dokidka_count_in_sales = db.Column(db.Boolean, default=False)  # Учитывать в продажах
    dokidka_count_in_purchases = db.Column(db.Boolean, default=False)  # Учитывать в покупках
    internal_transfer_amount = db.Column(db.Numeric(15, 2), default=0)  # Новое поле: внутренний перевод
    internal_transfer_amount_rub = db.Column(db.Numeric(15, 2), default=0)  # Сумма внутреннего перевода в рублях
    internal_transfer_platform = db.Column(db.String(20), default='bybit')  # Платформа для внутреннего перевода
    internal_transfer_account = db.Column(db.String(100), default='')  # Аккаунт для внутреннего перевода
    internal_transfer_count_in_sales = db.Column(db.Boolean, default=False)  # Учитывать в продажах
    internal_transfer_count_in_purchases = db.Column(db.Boolean, default=False)  # Учитывать в покупках
    dokidka_comment = db.Column(db.Text, default='')
    internal_transfer_comment = db.Column(db.Text, default='')
    # Файлы выгрузки
    bybit_file = db.Column(db.String(255), default=None)  # путь к файлу выгрузки Bybit
    bybit_btc_file = db.Column(db.String(255), default=None)  # путь к файлу выгрузки Bybit BTC (опционально)
    htx_file = db.Column(db.String(255), default=None)    # путь к файлу выгрузки HTX
    bliss_file = db.Column(db.String(255), default=None)  # путь к файлу выгрузки Bliss
    # Фотографии
    start_photo = db.Column(db.String(255), default=None) # фото начала смены
    end_photo = db.Column(db.String(255), default=None)   # фото конца смены
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    bybit_requests = db.Column(db.Integer, default=0)
    htx_requests = db.Column(db.Integer, default=0)
    bliss_requests = db.Column(db.Integer, default=0)
    # Новые поля для дат сделок по площадкам
    bybit_first_trade = db.Column(db.String(100), default='')
    bybit_last_trade = db.Column(db.String(100), default='')
    htx_first_trade = db.Column(db.String(100), default='')
    htx_last_trade = db.Column(db.String(100), default='')
    bliss_first_trade = db.Column(db.String(100), default='')
    bliss_last_trade = db.Column(db.String(100), default='')
    gate_first_trade = db.Column(db.String(100), default='')
    gate_last_trade = db.Column(db.String(100), default='')
    appeal_amount = db.Column(db.Numeric(15, 2), default=0)
    appeal_amount_rub = db.Column(db.Numeric(15, 2), default=0)  # Сумма апелляции в рублях
    appeal_platform = db.Column(db.String(20), default='bybit')  # Платформа для апелляции
    appeal_account = db.Column(db.String(100), default='')  # Аккаунт для апелляции
    appeal_comment = db.Column(db.Text, default='')
    appeal_deducted = db.Column(db.Boolean, default=False)  # Новое поле: вычитать ли аппеляцию из прибыли
    appeal_count_in_sales = db.Column(db.Boolean, default=False)  # Учитывать в продажах
    appeal_count_in_purchases = db.Column(db.Boolean, default=False)  # Учитывать в покупках
    # Время начала и окончания смены по МСК
    shift_start_time = db.Column(db.DateTime, default=None)  # Время начала смены
    shift_end_time = db.Column(db.DateTime, default=None)    # Время окончания смены

class OrderDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shift_report_id = db.Column(db.Integer, db.ForeignKey('shift_report.id'), nullable=False)
    order_id = db.Column(db.String(100), nullable=False)
    symbol = db.Column(db.String(20), nullable=False)
    side = db.Column(db.String(10), nullable=False)  # 'buy' или 'sell'
    quantity = db.Column(db.Numeric(15, 8), nullable=False)
    price = db.Column(db.Numeric(15, 8), nullable=False)
    total_usdt = db.Column(db.Numeric(15, 2), nullable=False)
    fees_usdt = db.Column(db.Numeric(15, 2), default=0)
    status = db.Column(db.String(20), nullable=False)  # 'success', 'failed', 'pending'
    executed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class InitialBalance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(20), nullable=False)
    account_name = db.Column(db.String(100), nullable=False)
    balance = db.Column(db.Numeric(15, 2), nullable=False, default=0)

class AccountBalanceHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    account_name = db.Column(db.String(100), nullable=False)
    platform = db.Column(db.String(20), nullable=False)
    shift_date = db.Column(db.Date, nullable=False)
    shift_type = db.Column(db.String(20), nullable=False)
    balance = db.Column(db.Numeric(15, 2), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=True)
    employee_name = db.Column(db.String(100), nullable=True)
    balance_type = db.Column(db.String(10), nullable=False, default='end')  # start или end

class Order(db.Model):
    """Модель для хранения ордеров от расширения Bybit"""
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(100), nullable=False, unique=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    platform = db.Column(db.String(20), nullable=False, default='bybit')
    account_name = db.Column(db.String(100), nullable=False)
    symbol = db.Column(db.String(20), nullable=False)
    side = db.Column(db.String(10), nullable=False)  # 'buy' или 'sell'
    quantity = db.Column(db.Numeric(15, 8), nullable=False)
    price = db.Column(db.Numeric(15, 8), nullable=False)
    total_usdt = db.Column(db.Numeric(15, 2), nullable=False)
    fees_usdt = db.Column(db.Numeric(15, 2), default=0)
    status = db.Column(db.String(20), nullable=False)  # 'filled', 'canceled', 'pending', 'appealed', 'dokidka', 'internal_transfer', 'scam'
    count_in_sales = db.Column(db.Boolean, default=False)  # Учитывать в продажах
    count_in_purchases = db.Column(db.Boolean, default=False)  # Учитывать в покупках
    executed_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связь с сотрудником
    employee = db.relationship('Employee', backref='orders')

class EmployeeScamHistory(db.Model):
    """Модель для хранения истории скамов сотрудников"""
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    shift_report_id = db.Column(db.Integer, db.ForeignKey('shift_report.id'), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    comment = db.Column(db.Text, default='')
    date = db.Column(db.Date, nullable=False)  # Дата отчета, в котором был скам
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи с другими таблицами
    employee = db.relationship('Employee', backref='scam_history')
    shift_report = db.relationship('ShiftReport', backref='scam_history')

class SalarySettings(db.Model):
    """Модель для хранения настроек расчета зарплаты"""
    id = db.Column(db.Integer, primary_key=True)
    base_percent = db.Column(db.Integer, nullable=False, default=30)  # Базовый процент от прибыли
    min_daily_profit = db.Column(db.Float, nullable=False, default=100.0)  # Минимальная средняя ежедневная прибыль (USDT)
    bonus_percent = db.Column(db.Integer, nullable=False, default=5)  # Бонус за превышение плана
    bonus_profit_threshold = db.Column(db.Float, nullable=False, default=150.0)  # Порог прибыли для получения бонуса (USDT)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# API Endpoints
@app.route('/')
def index():
    return send_from_directory('templates', 'index.html')

@app.route('/api/employees', methods=['GET'])
def get_employees():
    employees = Employee.query.all()
    return jsonify([
        {
            'id': e.id,
            'name': e.name,
            'telegram': e.telegram,
            'created_at': e.created_at,
            'salary_percent': e.salary_percent
        } for e in employees
    ])

@app.route('/api/employees', methods=['POST'])
def create_employee():
    """Создаёт нового сотрудника. Ожидает JSON с полями name и telegram."""
    try:
        # Валидация входных данных
        data = request.json
        if not data or not data.get('name') or not data.get('telegram'):
            return jsonify({'error': 'Необходимо указать имя и telegram'}), 400
        employee = Employee(
            name=data['name'],
            telegram=data['telegram']
        )
        db.session.add(employee)
        db.session.commit()
        return jsonify({'id': employee.id, 'message': 'Employee created successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка при создании сотрудника: {str(e)}'}), 500

@app.route('/api/employees/<int:employee_id>', methods=['DELETE'])
def delete_employee(employee_id):
    """Удаляет сотрудника по id. Требует пароль администратора в JSON."""
    try:
        data = request.get_json()
        if not validate_admin_password(data):
            return jsonify({'error': 'Неверный пароль'}), 403
        employee = db.session.get(Employee, employee_id)
        if not employee:
            return jsonify({'error': 'Сотрудник не найден'}), 404
        db.session.delete(employee)
        db.session.commit()
        return jsonify({'message': 'Сотрудник удален'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка при удалении сотрудника: {str(e)}'}), 500

@app.route('/api/employees/<int:employee_id>', methods=['PUT'])
def update_employee(employee_id):
    data = request.json
    emp = db.session.get(Employee, employee_id)
    if not emp:
        return jsonify({'error': 'Employee not found'}), 404
    if 'name' in data:
        emp.name = data['name']
    if 'telegram' in data:
        emp.telegram = data['telegram']
    if 'salary_percent' in data:
        try:
            emp.salary_percent = float(data['salary_percent'])
        except Exception:
            return jsonify({'error': 'Invalid salary_percent'}), 400
    db.session.commit()
    return jsonify({'message': 'Employee updated'})

@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    accounts = Account.query.filter_by(is_active=True).all()
    return jsonify([{
        'id': a.id,
        'employee_id': a.employee_id,
        'platform': a.platform,
        'account_name': a.account_name
    } for a in accounts])

@app.route('/api/accounts', methods=['POST'])
def create_account():
    """Создаёт новый аккаунт. Ожидает JSON с platform и account_name."""
    try:
        # Валидация входных данных
        data = request.json
        if not data or not data.get('platform') or not data.get('account_name'):
            return jsonify({'error': 'Необходимо указать platform и account_name'}), 400
        account = Account(
            platform=data['platform'],
            account_name=data['account_name']
        )
        db.session.add(account)
        db.session.commit()
        return jsonify({'id': account.id, 'message': 'Account created successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка при создании аккаунта: {str(e)}'}), 500

@app.route('/api/accounts/<int:account_id>', methods=['DELETE'])
def delete_account(account_id):
    """Удаляет аккаунт по id. Требует пароль администратора в JSON."""
    try:
        data = request.get_json()
        if not validate_admin_password(data):
            return jsonify({'error': 'Неверный пароль'}), 403
        account = db.session.get(Account, account_id)
        if not account:
            return jsonify({'error': 'Аккаунт не найден'}), 404
        db.session.delete(account)
        db.session.commit()
        return jsonify({'message': 'Аккаунт удален'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка при удалении аккаунта: {str(e)}'}), 500

@app.route('/api/reports', methods=['GET'])
def get_reports():
    """Возвращает список всех сменных отчётов с фильтрами по дате, сотруднику и отделу."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    employee_id = request.args.get('employee_id')
    department = request.args.get('department')
    
    query = ShiftReport.query
    
    if start_date:
        query = query.filter(ShiftReport.shift_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(ShiftReport.shift_date <= datetime.strptime(end_date, '%Y-%m-%d').date())
    if employee_id:
        query = query.filter(ShiftReport.employee_id == int(employee_id))
    if department:
        query = query.filter(ShiftReport.department == department)
    
    reports = query.all()
    return jsonify([{
        'id': r.id,
        'employee_id': r.employee_id,
        'shift_date': r.shift_date.isoformat(),
        'shift_start_date': r.shift_start_date.isoformat() if r.shift_start_date else None,
        'shift_end_date': r.shift_end_date.isoformat() if r.shift_end_date else None,
        'shift_type': r.shift_type,
        'department': r.department,
        'total_requests': r.total_requests,
        'balances_json': r.balances_json,
        'scam_amount': float(r.scam_amount),
        'scam_amount_rub': float(r.scam_amount_rub) if r.scam_amount_rub is not None else 0,
        'scam_platform': r.scam_platform,
        'scam_account': r.scam_account,
        'scam_comment': r.scam_comment,

        'scam_count_in_sales': r.scam_count_in_sales,
        'scam_count_in_purchases': r.scam_count_in_purchases,
        'dokidka_amount': float(r.dokidka_amount),
        'dokidka_amount_rub': float(r.dokidka_amount_rub) if r.dokidka_amount_rub is not None else 0,
        'dokidka_platform': r.dokidka_platform,
        'dokidka_account': r.dokidka_account,
        'dokidka_comment': r.dokidka_comment,
        'dokidka_count_in_sales': r.dokidka_count_in_sales,
        'dokidka_count_in_purchases': r.dokidka_count_in_purchases,
        'internal_transfer_amount': float(r.internal_transfer_amount),
        'internal_transfer_amount_rub': float(r.internal_transfer_amount_rub) if r.internal_transfer_amount_rub is not None else 0,
        'internal_transfer_platform': r.internal_transfer_platform,
        'internal_transfer_account': r.internal_transfer_account,
        'internal_transfer_comment': r.internal_transfer_comment,
        'internal_transfer_count_in_sales': r.internal_transfer_count_in_sales,
        'internal_transfer_count_in_purchases': r.internal_transfer_count_in_purchases,
        'bybit_file': r.bybit_file,
        'bybit_btc_file': r.bybit_btc_file,
        'htx_file': r.htx_file,
        'bliss_file': r.bliss_file,
        'start_photo': r.start_photo,
        'end_photo': r.end_photo,
        'bybit_requests': r.bybit_requests,
        'htx_requests': r.htx_requests,
        'bliss_requests': r.bliss_requests,
        'bybit_first_trade': r.bybit_first_trade,
        'bybit_last_trade': r.bybit_last_trade,
        'htx_first_trade': r.htx_first_trade,
        'htx_last_trade': r.htx_last_trade,
        'bliss_first_trade': r.bliss_first_trade,
        'bliss_last_trade': r.bliss_last_trade,
        'gate_first_trade': r.gate_first_trade,
        'gate_last_trade': r.gate_last_trade,
        'appeal_amount': float(getattr(r, 'appeal_amount', 0) or 0),
        'appeal_amount_rub': float(getattr(r, 'appeal_amount_rub', 0) or 0),
        'appeal_platform': getattr(r, 'appeal_platform', 'bybit'),
        'appeal_account': getattr(r, 'appeal_account', ''),
        'appeal_comment': getattr(r, 'appeal_comment', ''),
        'appeal_count_in_sales': getattr(r, 'appeal_count_in_sales', False),
        'appeal_count_in_purchases': getattr(r, 'appeal_count_in_purchases', False),
        'shift_start_time': r.shift_start_time.isoformat() if r.shift_start_time else None,
        'shift_end_time': r.shift_end_time.isoformat() if r.shift_end_time else None
    } for r in reports])

def parse_bool(value):
    """Преобразует строковое значение в булево"""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on')
    return bool(value)

def safe_float(value, default=0.0):
    """Безопасно преобразует значение в float, возвращая default если не удается"""
    if value is None or value == '':
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int(value, default=0):
    """Безопасно преобразует значение в int, возвращая default если не удается"""
    if value is None or value == '':
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def save_report_file(file, platform, report_id):
    """Сохраняет файл выгрузки для отчета"""
    if not file or not file.filename:
        return None
        
    # Создаем безопасное имя файла
    filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    # Сохраняем файл
    file.save(file_path)
    
    # Обновляем отчет с путем к файлу
    report = ShiftReport.query.get(report_id)
    if report:
        if platform == 'bybit':
            report.bybit_file = filename
        elif platform == 'bybit_btc':
            report.bybit_btc_file = filename
        elif platform == 'htx':
            report.htx_file = filename
        elif platform == 'bliss':
            report.bliss_file = filename
        db.session.commit()
    
    return file_path

@app.route('/api/reports', methods=['POST'])
def create_report():
    """Создаёт сменный отчёт. Ожидает JSON или multipart/form-data с основными полями смены и файлами."""
    try:
        # Валидация и обработка данных/файлов
        if request.content_type and request.content_type.startswith('multipart/form-data'):
            form = request.form
            files = request.files
            
            # Валидация обязательных полей
            required_fields = ['employee_id', 'shift_date', 'shift_type']
            for field in required_fields:
                if not form.get(field):
                    return jsonify({'error': f'Поле {field} обязательно для заполнения'}), 400
            
            # Сохраняем файлы выгрузок и фото с валидацией
            file_keys = ['bybit_file', 'bybit_btc_file', 'htx_file', 'bliss_file', 'start_photo', 'end_photo']
            file_paths = {}
            
            for key in file_keys:
                if key in files and files[key].filename:
                    file = files[key]
                    if file and allowed_file(file.filename):
                        if not validate_file_size(file):
                            return jsonify({'error': f'Файл {file.filename} слишком большой (максимум 16MB)'}), 400
                        filename = secure_filename(file.filename)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"{timestamp}_{filename}"
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file.save(file_path)
                        file_paths[key] = filename
                    else:
                        return jsonify({'error': f'Недопустимый тип файла: {file.filename}'}), 400
                else:
                    file_paths[key] = None

            # Валидация числовых полей с безопасным преобразованием
            try:
                bybit_requests = safe_int(form.get('bybit_requests', 0))
                htx_requests = safe_int(form.get('htx_requests', 0))
                bliss_requests = safe_int(form.get('bliss_requests', 0))
                if any(x < 0 for x in [bybit_requests, htx_requests, bliss_requests]):
                    return jsonify({'error': 'Количество заявок не может быть отрицательным'}), 400
            except Exception as e:
                return jsonify({'error': f'Ошибка валидации числовых полей: {str(e)}'}), 400

            # Валидация JSON балансов
            try:
                balances_json = form.get('balances_json', '{}')
                json.loads(balances_json)  # Проверяем корректность JSON
            except json.JSONDecodeError:
                return jsonify({'error': 'Неверный формат JSON балансов'}), 400

            total_requests = bybit_requests + htx_requests + bliss_requests

            report = ShiftReport(
                employee_id=safe_int(form['employee_id']),
                shift_date=datetime.strptime(form['shift_date'], '%Y-%m-%d').date(),
                shift_type=form['shift_type'],
                department=form.get('department', 'first'),
                total_requests=total_requests,
                balances_json=balances_json,
                scam_amount=safe_float(form.get('scam_amount', 0)),
                scam_comment=form.get('scam_comment', ''),

                dokidka_amount=safe_float(form.get('dokidka_amount', 0)),
                dokidka_comment=form.get('dokidka_comment', ''),
                internal_transfer_amount=safe_float(form.get('internal_transfer_amount', 0)),
                internal_transfer_comment=form.get('internal_transfer_comment', ''),
                bybit_file=file_paths['bybit_file'],
                bybit_btc_file=file_paths['bybit_btc_file'],
                htx_file=file_paths['htx_file'],
                bliss_file=file_paths['bliss_file'],
                start_photo=file_paths['start_photo'],
                end_photo=file_paths['end_photo'],
                bybit_requests=bybit_requests,
                htx_requests=htx_requests,
                bliss_requests=bliss_requests,
                bybit_first_trade=form.get('bybit_first_trade', ''),
                bybit_last_trade=form.get('bybit_last_trade', ''),
                htx_first_trade=form.get('htx_first_trade', ''),
                htx_last_trade=form.get('htx_last_trade', ''),
                bliss_first_trade=form.get('bliss_first_trade', ''),
                bliss_last_trade=form.get('bliss_last_trade', ''),
                gate_first_trade=form.get('gate_first_trade', ''),
                gate_last_trade=form.get('gate_last_trade', ''),
                appeal_amount=safe_float(form.get('appeal_amount', 0)),
                appeal_comment=form.get('appeal_comment', ''),
                shift_start_time=datetime.strptime(form['shift_start_time'], '%Y-%m-%dT%H:%M') if form.get('shift_start_time') else None,
                shift_end_time=datetime.strptime(form['shift_end_time'], '%Y-%m-%dT%H:%M') if form.get('shift_end_time') else None
            )
            db.session.add(report)
            db.session.commit()
            
            # Обрабатываем файлы выгрузок с автоматической проверкой времени
            files_data = {}
            if file_paths['bybit_file']:
                files_data['bybit'] = os.path.join(app.config['UPLOAD_FOLDER'], file_paths['bybit_file'])
            if file_paths['bybit_btc_file']:
                files_data['bybit_btc'] = os.path.join(app.config['UPLOAD_FOLDER'], file_paths['bybit_btc_file'])
            if file_paths['htx_file']:
                files_data['htx'] = os.path.join(app.config['UPLOAD_FOLDER'], file_paths['htx_file'])
            if file_paths['bliss_file']:
                files_data['bliss'] = os.path.join(app.config['UPLOAD_FOLDER'], file_paths['bliss_file'])
            
            # Обрабатываем файлы с проверкой времени
            if files_data and report.shift_start_time and report.shift_end_time:
                file_stats = process_shift_files(
                    report.id,
                    report.employee_id,
                    report.shift_start_time,
                    report.shift_end_time,
                    files_data,
                    report.shift_start_date,
                    report.shift_end_date
                )
                
                return jsonify({
                    'id': report.id, 
                    'message': 'Report created successfully',
                    'file_processing': file_stats
                })
            else:
                # Привязываем ордера к сотруднику на основе времени смены
                from utils import link_orders_to_employee
                linked_orders = link_orders_to_employee(db.session, report)

                return jsonify({
                    'id': report.id, 
                    'message': 'Report created successfully',
                    'linked_orders': linked_orders
                })
        
        elif request.content_type and request.content_type.startswith('application/json'):
            # Обработка JSON данных
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Отсутствуют данные в запросе'}), 400
            
            # Валидация обязательных полей
            required_fields = ['employee_id', 'shift_date', 'shift_type']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({'error': f'Поле {field} обязательно для заполнения'}), 400
            
            # Валидация числовых полей с безопасным преобразованием
            try:
                bybit_requests = safe_int(data.get('bybit_requests', 0))
                htx_requests = safe_int(data.get('htx_requests', 0))
                bliss_requests = safe_int(data.get('bliss_requests', 0))
                if any(x < 0 for x in [bybit_requests, htx_requests, bliss_requests]):
                    return jsonify({'error': 'Количество заявок не может быть отрицательным'}), 400
            except Exception as e:
                return jsonify({'error': f'Ошибка валидации числовых полей: {str(e)}'}), 400

            # Валидация JSON балансов
            try:
                balances_json = data.get('balances_json', '{}')
                if isinstance(balances_json, dict):
                    balances_json = json.dumps(balances_json)
                json.loads(balances_json)  # Проверяем корректность JSON
            except json.JSONDecodeError:
                return jsonify({'error': 'Неверный формат JSON балансов'}), 400

            total_requests = bybit_requests + htx_requests + bliss_requests

            report = ShiftReport(
                employee_id=safe_int(data['employee_id']),
                shift_date=datetime.strptime(data['shift_date'], '%Y-%m-%d').date(),
                shift_type=data['shift_type'],
                department=data.get('department', 'first'),
                total_requests=total_requests,
                balances_json=balances_json,
                scam_amount=safe_float(data.get('scam_amount', 0)),
                scam_comment=data.get('scam_comment', ''),

                dokidka_amount=safe_float(data.get('dokidka_amount', 0)),
                dokidka_comment=data.get('dokidka_comment', ''),
                internal_transfer_amount=safe_float(data.get('internal_transfer_amount', 0)),
                internal_transfer_comment=data.get('internal_transfer_comment', ''),
                bybit_file=data.get('bybit_file'),
                bybit_btc_file=data.get('bybit_btc_file'),
                htx_file=data.get('htx_file'),
                bliss_file=data.get('bliss_file'),
                start_photo=data.get('start_photo'),
                end_photo=data.get('end_photo'),
                bybit_requests=bybit_requests,
                htx_requests=htx_requests,
                bliss_requests=bliss_requests,
                bybit_first_trade=data.get('bybit_first_trade', ''),
                bybit_last_trade=data.get('bybit_last_trade', ''),
                htx_first_trade=data.get('htx_first_trade', ''),
                htx_last_trade=data.get('htx_last_trade', ''),
                bliss_first_trade=data.get('bliss_first_trade', ''),
                bliss_last_trade=data.get('bliss_last_trade', ''),
                gate_first_trade=data.get('gate_first_trade', ''),
                gate_last_trade=data.get('gate_last_trade', ''),
                appeal_amount=safe_float(data.get('appeal_amount', 0)),
                appeal_comment=data.get('appeal_comment', ''),
                shift_start_time=datetime.strptime(data['shift_start_time'], '%Y-%m-%dT%H:%M') if data.get('shift_start_time') else None,
                shift_end_time=datetime.strptime(data['shift_end_time'], '%Y-%m-%dT%H:%M') if data.get('shift_end_time') else None
            )
            db.session.add(report)
            db.session.commit()
            
            # Обрабатываем файлы выгрузок с автоматической проверкой времени
            files_data = {}
            if data.get('bybit_file'):
                files_data['bybit'] = data['bybit_file']
            if data.get('bybit_btc_file'):
                files_data['bybit_btc'] = data['bybit_btc_file']
            if data.get('htx_file'):
                files_data['htx'] = data['htx_file']
            if data.get('bliss_file'):
                files_data['bliss'] = data['bliss_file']
            
            # Обрабатываем файлы с проверкой времени
            if files_data and report.shift_start_time and report.shift_end_time:
                file_stats = process_shift_files(
                    report.id,
                    report.employee_id,
                    report.shift_start_time,
                    report.shift_end_time,
                    files_data,
                    report.shift_start_date,
                    report.shift_end_date
                )
                
                return jsonify({
                    'id': report.id, 
                    'message': 'Report created successfully',
                    'file_processing': file_stats
                })
            else:
                # Привязываем ордера к сотруднику на основе времени смены
                from utils import link_orders_to_employee
                linked_orders = link_orders_to_employee(db.session, report)

                return jsonify({
                    'id': report.id, 
                    'message': 'Report created successfully',
                    'linked_orders': linked_orders
                })
        
        else:
            # Неподдерживаемый тип контента
            return jsonify({'error': 'Неподдерживаемый тип контента. Используйте multipart/form-data или application/json'}), 400
            
    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка валидации данных: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Ошибка при создании отчета: {str(e)}')
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/api/reports/<int:report_id>', methods=['DELETE'])
def delete_report(report_id):
    """Удаляет сменный отчёт по id. Требует пароль администратора в JSON."""
    try:
        data = request.get_json()
        if not validate_admin_password(data):
            return jsonify({'error': 'Неверный пароль'}), 403
        report = db.session.get(ShiftReport, report_id)
        if not report:
            return jsonify({'error': 'Отчет не найден'}), 404
        db.session.delete(report)
        db.session.commit()
        return jsonify({'message': 'Отчет удален'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка при удалении отчета: {str(e)}'}), 500

def calculate_employee_stats(reports, employees, db):
    """Вычисляет статистику по сотрудникам для дашборда (кол-во заявок, прибыль и т.д.)."""
    stats = []
    for emp in employees:
        emp_reports = [r for r in reports if r.employee_id == emp.id]
        emp_requests = sum((r.bybit_requests or 0) + (r.htx_requests or 0) + (r.bliss_requests or 0) for r in emp_reports)
        
        # Используем ту же логику, что и в дашборде (API статистики)
        emp_profit = 0.0
        for r in emp_reports:
            try:
                # Получаем ордера за период смены (как в API статистики)
                query = Order.query.filter(Order.employee_id == r.employee_id)
                query = query.filter(Order.platform != 'bybit_btc')  # Исключаем BTC как в API
                query = query.filter(~Order.status.in_(['canceled', 'expired', 'failed']))
                query = query.filter(Order.executed_at >= r.shift_start_time)
                query = query.filter(Order.executed_at <= r.shift_end_time)
                orders = query.all()
                
                # Статистика по сторонам (buy/sell) - используем только завершенные ордера
                completed_orders = [o for o in orders if o.status == 'filled']
                buy_orders = [o for o in completed_orders if o.side == 'buy']
                sell_orders = [o for o in completed_orders if o.side == 'sell']
                
                # Расчет объемов только для завершенных ордеров
                buy_volume_usdt = sum(float(o.quantity) for o in buy_orders)
                sell_volume_usdt = sum(float(o.quantity) for o in sell_orders)
                
                # Специальные ордера (как в API статистики)
                special_statuses = ['dokidka', 'internal_transfer', 'appealed', 'scam']
                special_orders_query = Order.query.filter(Order.status.in_(special_statuses))
                special_orders_query = special_orders_query.filter(Order.employee_id == r.employee_id)
                special_orders_query = special_orders_query.filter(Order.platform != 'bybit_btc')
                special_orders_query = special_orders_query.filter(Order.executed_at >= r.shift_start_time)
                special_orders_query = special_orders_query.filter(Order.executed_at <= r.shift_end_time)
                special_orders = special_orders_query.all()
                
                # Добавляем покупки из специальных ордеров (с учетом чекбоксов)
                special_buys_usdt = 0
                for order in special_orders:
                    if order.count_in_purchases:
                        order_amount_usdt = float(order.quantity or 0)
                        special_buys_usdt += order_amount_usdt
                
                # Общие покупки по формуле
                total_buys_usdt = buy_volume_usdt + special_buys_usdt
                
                # Продажи из специальных ордеров (с учетом чекбоксов)
                special_sales_usdt = 0
                for order in special_orders:
                    if order.count_in_sales:
                        order_amount_usdt = float(order.quantity or 0)
                        special_sales_usdt += order_amount_usdt
                
                # Общие продажи по формуле
                total_sales_usdt = sell_volume_usdt + special_sales_usdt
                
                # Рассчитываем прибыль в USDT (покупки - продажи с учетом переводов и скама)
                report_profit = total_buys_usdt - total_sales_usdt
                emp_profit += report_profit
                
            except Exception as e:
                print(f"[EMPLOYEE_STATS] Ошибка расчета прибыли для отчета {r.id}: {e}")
                continue
        
        emp_shifts = len(emp_reports)
        avg_profit_per_shift = emp_profit / emp_shifts if emp_shifts else 0
        stats.append({
            'id': emp.id,
            'name': emp.name,
            'telegram': emp.telegram,
            'total_requests': emp_requests,
            'net_profit': round(emp_profit,2),
            'total_shifts': emp_shifts,
            'avg_profit_per_shift': round(avg_profit_per_shift,2)
        })
    return stats

def calculate_employee_stats_by_department(reports, employees, db):
    """Вычисляет статистику по сотрудникам отдельно для каждого отдела."""
    first_department_stats = []
    second_department_stats = []
    
    for emp in employees:
        # Получаем отчеты сотрудника по отделам
        first_dept_reports = [r for r in reports if r.employee_id == emp.id and r.department == 'first']
        second_dept_reports = [r for r in reports if r.employee_id == emp.id and r.department == 'second']
        
        # Статистика для первого отдела
        if first_dept_reports:
            emp_requests = sum((r.bybit_requests or 0) + (r.htx_requests or 0) + (r.bliss_requests or 0) for r in first_dept_reports)
            
            # Используем ту же логику, что и в дашборде (API статистики)
            emp_profit = 0.0
            for r in first_dept_reports:
                try:
                    # Получаем ордера за период смены (как в API статистики)
                    query = Order.query.filter(Order.employee_id == r.employee_id)
                    query = query.filter(Order.platform != 'bybit_btc')  # Исключаем BTC как в API
                    query = query.filter(~Order.status.in_(['canceled', 'expired', 'failed']))
                    query = query.filter(Order.executed_at >= r.shift_start_time)
                    query = query.filter(Order.executed_at <= r.shift_end_time)
                    orders = query.all()
                    
                    # Статистика по сторонам (buy/sell) - используем только завершенные ордера
                    completed_orders = [o for o in orders if o.status == 'filled']
                    buy_orders = [o for o in completed_orders if o.side == 'buy']
                    sell_orders = [o for o in completed_orders if o.side == 'sell']
                    
                    # Расчет объемов только для завершенных ордеров
                    buy_volume_usdt = sum(float(o.quantity) for o in buy_orders)
                    sell_volume_usdt = sum(float(o.quantity) for o in sell_orders)
                    
                    # Специальные ордера (как в API статистики)
                    special_statuses = ['dokidka', 'internal_transfer', 'appealed', 'scam']
                    special_orders_query = Order.query.filter(Order.status.in_(special_statuses))
                    special_orders_query = special_orders_query.filter(Order.employee_id == r.employee_id)
                    special_orders_query = special_orders_query.filter(Order.platform != 'bybit_btc')
                    special_orders_query = special_orders_query.filter(Order.executed_at >= r.shift_start_time)
                    special_orders_query = special_orders_query.filter(Order.executed_at <= r.shift_end_time)
                    special_orders = special_orders_query.all()
                    
                    # Добавляем покупки из специальных ордеров (с учетом чекбоксов)
                    special_buys_usdt = 0
                    for order in special_orders:
                        if order.count_in_purchases:
                            order_amount_usdt = float(order.quantity or 0)
                            special_buys_usdt += order_amount_usdt
                    
                    # Общие покупки по формуле
                    total_buys_usdt = buy_volume_usdt + special_buys_usdt
                    
                    # Продажи из специальных ордеров (с учетом чекбоксов)
                    special_sales_usdt = 0
                    for order in special_orders:
                        if order.count_in_sales:
                            order_amount_usdt = float(order.quantity or 0)
                            special_sales_usdt += order_amount_usdt
                    
                    # Общие продажи по формуле
                    total_sales_usdt = sell_volume_usdt + special_sales_usdt
                    
                    # Рассчитываем прибыль в USDT (покупки - продажи с учетом переводов и скама)
                    report_profit = total_buys_usdt - total_sales_usdt
                    emp_profit += report_profit
                    
                except Exception as e:
                    print(f"[EMPLOYEE_STATS_DEPT] Ошибка расчета прибыли для отчета {r.id}: {e}")
                    continue
            
            emp_shifts = len(first_dept_reports)
            avg_profit_per_shift = emp_profit / emp_shifts if emp_shifts else 0
            first_department_stats.append({
                'id': emp.id,
                'name': emp.name,
                'telegram': emp.telegram,
                'total_requests': emp_requests,
                'net_profit': round(emp_profit,2),
                'total_shifts': emp_shifts,
                'avg_profit_per_shift': round(avg_profit_per_shift,2)
            })
        
        # Статистика для второго отдела
        if second_dept_reports:
            emp_requests = sum((r.bybit_requests or 0) + (r.htx_requests or 0) + (r.bliss_requests or 0) for r in second_dept_reports)
            
            # Используем ту же логику, что и в дашборде (API статистики)
            emp_profit = 0.0
            for r in second_dept_reports:
                try:
                    # Получаем ордера за период смены (как в API статистики)
                    query = Order.query.filter(Order.employee_id == r.employee_id)
                    query = query.filter(Order.platform != 'bybit_btc')  # Исключаем BTC как в API
                    query = query.filter(~Order.status.in_(['canceled', 'expired', 'failed']))
                    query = query.filter(Order.executed_at >= r.shift_start_time)
                    query = query.filter(Order.executed_at <= r.shift_end_time)
                    orders = query.all()
                    
                    # Статистика по сторонам (buy/sell) - используем только завершенные ордера
                    completed_orders = [o for o in orders if o.status == 'filled']
                    buy_orders = [o for o in completed_orders if o.side == 'buy']
                    sell_orders = [o for o in completed_orders if o.side == 'sell']
                    
                    # Расчет объемов только для завершенных ордеров
                    buy_volume_usdt = sum(float(o.quantity) for o in buy_orders)
                    sell_volume_usdt = sum(float(o.quantity) for o in sell_orders)
                    
                    # Специальные ордера (как в API статистики)
                    special_statuses = ['dokidka', 'internal_transfer', 'appealed', 'scam']
                    special_orders_query = Order.query.filter(Order.status.in_(special_statuses))
                    special_orders_query = special_orders_query.filter(Order.employee_id == r.employee_id)
                    special_orders_query = special_orders_query.filter(Order.platform != 'bybit_btc')
                    special_orders_query = special_orders_query.filter(Order.executed_at >= r.shift_start_time)
                    special_orders_query = special_orders_query.filter(Order.executed_at <= r.shift_end_time)
                    special_orders = special_orders_query.all()
                    
                    # Добавляем покупки из специальных ордеров (с учетом чекбоксов)
                    special_buys_usdt = 0
                    for order in special_orders:
                        if order.count_in_purchases:
                            order_amount_usdt = float(order.quantity or 0)
                            special_buys_usdt += order_amount_usdt
                    
                    # Общие покупки по формуле
                    total_buys_usdt = buy_volume_usdt + special_buys_usdt
                    
                    # Продажи из специальных ордеров (с учетом чекбоксов)
                    special_sales_usdt = 0
                    for order in special_orders:
                        if order.count_in_sales:
                            order_amount_usdt = float(order.quantity or 0)
                            special_sales_usdt += order_amount_usdt
                    
                    # Общие продажи по формуле
                    total_sales_usdt = sell_volume_usdt + special_sales_usdt
                    
                    # Рассчитываем прибыль в USDT (покупки - продажи с учетом переводов и скама)
                    report_profit = total_buys_usdt - total_sales_usdt
                    emp_profit += report_profit
                    
                except Exception as e:
                    print(f"[EMPLOYEE_STATS_DEPT] Ошибка расчета прибыли для отчета {r.id}: {e}")
                    continue
            
            emp_shifts = len(second_dept_reports)
            avg_profit_per_shift = emp_profit / emp_shifts if emp_shifts else 0
            second_department_stats.append({
                'id': emp.id,
                'name': emp.name,
                'telegram': emp.telegram,
                'total_requests': emp_requests,
                'net_profit': round(emp_profit,2),
                'total_shifts': emp_shifts,
                'avg_profit_per_shift': round(avg_profit_per_shift,2)
            })
    
    return {
        'first_department': first_department_stats,
        'second_department': second_department_stats
    }

def calculate_last_reports(db, last_reports_query):
    """Формирует список последних смен с расчетом прибыли и балансов по площадкам для дашборда."""
    last_reports = []
    for r in last_reports_query:
        profit_data = calculate_profit_from_orders(db.session, r)
        try:
            balances = json.loads(r.balances_json or '{}')
        except json.JSONDecodeError:
            balances = {}
        emp = db.session.get(Employee, r.employee_id)
        employee_name = emp.name if emp else '—'
        platform_stats = {}
        for platform in ['bybit','htx','bliss','gate']:
            accounts_list = balances.get(platform, [])
            count = len(accounts_list)
            sum_delta = 0
            for acc in accounts_list:
                prev = find_prev_balance(db.session, acc.get('account_id') or acc.get('id'), platform, r)
                cur = float(acc.get('balance', 0)) if acc.get('balance') not in (None, '') else 0
                sum_delta += cur - prev
            platform_stats[platform] = {'count': count, 'delta': round(sum_delta,2)}
        profit = sum(platform_stats[p]['delta'] for p in platform_stats)
        scam = float(r.scam_amount or 0)
        transfer = float(r.dokidka_amount or 0)
        net_profit = profit - scam - transfer
        last_reports.append({
            'id': r.id,
            'employee_name': employee_name,
            'shift_date': r.shift_date.isoformat(),
            'shift_type': r.shift_type,
            'total_requests': r.total_requests,
            'profit': round(net_profit,2),
            'bybit_accounts': platform_stats['bybit']['count'],
            'bybit_delta': platform_stats['bybit']['delta'],
            'htx_accounts': platform_stats['htx']['count'],
            'htx_delta': platform_stats['htx']['delta'],
            'bliss_accounts': platform_stats['bliss']['count'],
            'bliss_delta': platform_stats['bliss']['delta'],
            'gate_accounts': platform_stats['gate']['count'],
            'gate_delta': platform_stats['gate']['delta'],
        })
    return last_reports

def calculate_account_balances(accounts, reports, db):
    """Вычисляет финальные балансы по всем аккаунтам для дашборда."""
    account_balances = {}
    for acc in accounts:
        account_balances[acc.id] = calculate_account_last_balance(db.session, acc.id, acc.platform, reports)
    return account_balances

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard_data():
    """Возвращает агрегированные данные для дашборда с поддержкой фильтрации по дате. Топ-3 сотрудников и общая прибыль всегда за текущий месяц."""
    from datetime import datetime, timedelta
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    if start_date and end_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
    reports = ShiftReport.query.filter(
        ShiftReport.shift_date >= start_date,
        ShiftReport.shift_date <= end_date
    ).all()
    # --- Общая прибыль за выбранный период (используем логику ордеров) ---
    total_profit = sum(calculate_profit_from_orders(db.session, r)['project_profit'] for r in reports)
    # --- Общий объем: сумма всех end_balance по всем аккаунтам на конец последней смены ---
    accounts = Account.query.filter_by(is_active=True).all()
    last_report = max(reports, key=lambda r: (r.shift_date, 0 if r.shift_type=='morning' else 1), default=None)
    total_volume = 0.0
    if last_report:
        try:
            balances = json.loads(last_report.balances_json or '{}')
        except:
            balances = {}
        for platform in ['bybit','htx','bliss','gate']:
            if balances.get(platform):
                for acc in balances[platform]:
                    end = float(acc.get('end_balance', 0) or 0)
                    total_volume += end
    total_requests = sum((r.bybit_requests or 0) + (r.htx_requests or 0) + (r.bliss_requests or 0) for r in reports)
    morning_profit = 0
    evening_profit = 0
    reports_with_net = []
    for r in reports:
        profit_data = calculate_profit_from_orders(db.session, r)
        net_profit = profit_data['project_profit']
        if r.shift_type == 'morning':
            morning_profit += net_profit
        elif r.shift_type == 'evening':
            evening_profit += net_profit
        reports_with_net.append({
            'id': r.id,
            'employee_id': r.employee_id,
            'shift_date': r.shift_date.isoformat(),
            'shift_type': r.shift_type,
            'total_requests': r.total_requests,
            'balances_json': r.balances_json,
            'scam_amount': float(r.scam_amount),
            'scam_comment': r.scam_comment,

            'dokidka_amount': float(r.dokidka_amount),
            'dokidka_comment': r.dokidka_comment,
            'internal_transfer_amount': float(r.internal_transfer_amount),
            'internal_transfer_comment': r.internal_transfer_comment,
            'bybit_file': r.bybit_file,
            'htx_file': r.htx_file,
            'bliss_file': r.bliss_file,
            'start_photo': r.start_photo,
            'end_photo': r.end_photo,
            'bybit_requests': r.bybit_requests,
            'htx_requests': r.htx_requests,
            'bliss_requests': r.bliss_requests,
            'net_profit': round(net_profit, 2)
        })
    # --- Статистика по сотрудникам (ТОП-3) и общая прибыль всегда за текущий календарный месяц ---
    today = datetime.now().date()
    month_start = today.replace(day=1)
    month_end = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    month_reports = ShiftReport.query.filter(
        ShiftReport.shift_date >= month_start,
        ShiftReport.shift_date <= month_end
    ).all()
    employees = Employee.query.filter_by(is_active=True).all()
    employee_stats = calculate_employee_stats(month_reports, employees, db)
    employee_stats_by_department = calculate_employee_stats_by_department(month_reports, employees, db)
    # ПРОСТАЯ СУММА ПРИБЫЛИ ИЗ ДЕТАЛЬНОГО ОТЧЕТА ЗА ТЕКУЩИЙ МЕСЯЦ
    month_total_profit = 0.0
    
    for r in month_reports:
        # Получаем прибыль из API статистики (точно так же, как в кратком/детальном отчете)
        try:
            # Используем ту же логику, что и в API статистики
            start_date = r.shift_date.strftime('%Y-%m-%d')
            end_date = r.shift_date.strftime('%Y-%m-%d')
            
            # Получаем ордера за период смены (как в API статистики)
            query = Order.query.filter(Order.employee_id == r.employee_id)
            query = query.filter(Order.platform != 'bybit_btc')  # Исключаем BTC как в API
            query = query.filter(~Order.status.in_(['canceled', 'expired', 'failed']))
            query = query.filter(Order.executed_at >= r.shift_start_time)
            query = query.filter(Order.executed_at <= r.shift_end_time)
            orders = query.all()
            
            # Статистика по сторонам (buy/sell) - используем только завершенные ордера
            completed_orders = [o for o in orders if o.status == 'filled']
            buy_orders = [o for o in completed_orders if o.side == 'buy']
            sell_orders = [o for o in completed_orders if o.side == 'sell']
            
            # Расчет объемов только для завершенных ордеров
            buy_volume_usdt = sum(float(o.quantity) for o in buy_orders)
            sell_volume_usdt = sum(float(o.quantity) for o in sell_orders)
            
            # Специальные ордера (как в API статистики)
            special_statuses = ['dokidka', 'internal_transfer', 'appealed', 'scam']
            special_orders_query = Order.query.filter(Order.status.in_(special_statuses))
            special_orders_query = special_orders_query.filter(Order.employee_id == r.employee_id)
            special_orders_query = special_orders_query.filter(Order.platform != 'bybit_btc')
            special_orders_query = special_orders_query.filter(Order.executed_at >= r.shift_start_time)
            special_orders_query = special_orders_query.filter(Order.executed_at <= r.shift_end_time)
            special_orders = special_orders_query.all()
            
            # Добавляем покупки из специальных ордеров (с учетом чекбоксов)
            special_buys_usdt = 0
            for order in special_orders:
                if order.count_in_purchases:
                    order_amount_usdt = float(order.quantity or 0)
                    special_buys_usdt += order_amount_usdt
            
            # Общие покупки по формуле
            total_buys_usdt = buy_volume_usdt + special_buys_usdt
            
            # Продажи из специальных ордеров (с учетом чекбоксов)
            special_sales_usdt = 0
            for order in special_orders:
                if order.count_in_sales:
                    order_amount_usdt = float(order.quantity or 0)
                    special_sales_usdt += order_amount_usdt
            
            # Общие продажи по формуле
            total_sales_usdt = sell_volume_usdt + special_sales_usdt
            
            # Рассчитываем прибыль в USDT (покупки - продажи с учетом переводов и скама)
            report_profit = total_buys_usdt - total_sales_usdt

            
        except Exception as e:
            print(f"[DASHBOARD] Ошибка расчета прибыли для отчета {r.id}: {e}")
            report_profit = 0
            
        month_total_profit += report_profit
    
    month_total_requests = sum((r.bybit_requests or 0) + (r.htx_requests or 0) + (r.bliss_requests or 0) for r in month_reports)
    # --- LAST REPORTS (3 последних смены) ---
    last_reports_query = ShiftReport.query.order_by(ShiftReport.shift_date.desc(), ShiftReport.created_at.desc()).limit(3).all()
    last_reports = calculate_last_reports(db, last_reports_query)
    dashboard = {
        'total_profit': round(total_profit,2),
        'month_total_profit': round(month_total_profit,2),
        'total_volume': round(total_volume,2),
        'total_requests': total_requests,
        'month_total_requests': month_total_requests,
        'morning_profit': round(morning_profit,2),
        'evening_profit': round(evening_profit,2),
        'employee_stats': employee_stats,
        'employee_stats_by_department': employee_stats_by_department,
        'last_reports': last_reports,
        'reports': reports_with_net,
        'profit_by_day': group_reports_by_day_net_profit(reports_with_net)
    }
    return jsonify(dashboard)

@app.route('/api/settings/balances', methods=['GET', 'POST'])
def settings_balances():
    """Получение и сохранение начальных балансов. POST требует пароль администратора."""
    if request.method == 'GET':
        # Возвращаем все начальные балансы
        balances = InitialBalance.query.all()
        return jsonify([
            {'id': b.id, 'platform': b.platform, 'account_name': b.account_name, 'balance': float(b.balance)}
            for b in balances
        ])
    elif request.method == 'POST':
        try:
            data = request.json
            if not validate_admin_password(data):
                return jsonify({'error': 'Неверный пароль'}), 403
            # Ожидаем список балансов: [{platform, account_name, balance}]
            if not data.get('balances') or not isinstance(data['balances'], list):
                return jsonify({'error': 'Необходимо передать список balances'}), 400
            InitialBalance.query.delete()
            for item in data.get('balances', []):
                if not item.get('platform') or not item.get('account_name'):
                    return jsonify({'error': 'Каждый баланс должен содержать platform и account_name'}), 400
                b = InitialBalance(
                    platform=item['platform'],
                    account_name=item['account_name'],
                    balance=item['balance']
                )
                db.session.add(b)
            db.session.commit()
            return jsonify({'message': 'Начальные балансы сохранены'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Ошибка при сохранении балансов: {str(e)}'}), 500



@app.route('/logout')
def logout():
    """Endpoint для выхода из системы"""
    # В данном случае просто перенаправляем на главную страницу
    # В реальном приложении здесь можно добавить очистку сессии
    return jsonify({'message': 'Выход выполнен успешно', 'redirect': '/'})

@app.route('/api/account-balance-history', methods=['GET'])
def get_account_balance_history():
    """Возвращает историю балансов аккаунтов с фильтрами, включая отдел."""
    query = AccountBalanceHistory.query
    account_id = request.args.get('account_id')
    platform = request.args.get('platform')
    employee_id = request.args.get('employee_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    department = request.args.get('department')
    if account_id:
        query = query.filter(AccountBalanceHistory.account_id == int(account_id))
    if platform:
        query = query.filter(AccountBalanceHistory.platform == platform)
    if employee_id:
        query = query.filter(AccountBalanceHistory.employee_id == int(employee_id))
    if start_date:
        query = query.filter(AccountBalanceHistory.shift_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(AccountBalanceHistory.shift_date <= datetime.strptime(end_date, '%Y-%m-%d').date())
    if department:
        # join с ShiftReport для фильтрации по отделу
        query = query.join(ShiftReport, (ShiftReport.shift_date == AccountBalanceHistory.shift_date) & (ShiftReport.employee_id == AccountBalanceHistory.employee_id)).filter(ShiftReport.department == department)
    history = query.order_by(AccountBalanceHistory.shift_date, AccountBalanceHistory.shift_type).all()
    return jsonify([
        {
            'id': h.id,
            'account_id': h.account_id,
            'account_name': h.account_name,
            'platform': h.platform,
            'shift_date': h.shift_date.isoformat(),
            'shift_type': h.shift_type,
            'balance': float(h.balance),
            'employee_id': h.employee_id,
            'employee_name': h.employee_name,
            'balance_type': h.balance_type,
        }
        for h in history
    ])

@app.route('/api/account-balance-history', methods=['POST'])
def add_account_balance_history():
    """Добавляет запись в историю балансов аккаунтов."""
    try:
        data = request.json
        if not data or not data.get('account_id') or not data.get('platform') or not data.get('shift_date') or not data.get('shift_type'):
            return jsonify({'error': 'Необходимо указать account_id, platform, shift_date, shift_type'}), 400
        history = AccountBalanceHistory(
            account_id=data['account_id'],
            account_name=data.get('account_name', ''),
            platform=data['platform'],
            shift_date=datetime.strptime(data['shift_date'], '%Y-%m-%d').date(),
            shift_type=data['shift_type'],
            balance=data.get('balance', 0),
            employee_id=data.get('employee_id'),
            employee_name=data.get('employee_name', ''),
            balance_type=data.get('balance_type', 'end')
        )
        db.session.add(history)
        db.session.commit()
        return jsonify({'id': history.id, 'message': 'Account balance history added'})
    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка валидации данных: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Ошибка при добавлении в историю балансов: {str(e)}')
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

# Добавляю новые API endpoints для безопасной аутентификации
@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """API endpoint для аутентификации пользователей"""
    try:
        data = request.json
        if not data or not data.get('password'):
            return jsonify({'error': 'Пароль обязателен'}), 400
        
        # Проверяем пароль приложения
        app_password = os.environ.get('APP_PASSWORD', '7605203')
        if data['password'] == app_password:
            return jsonify({'success': True, 'message': 'Аутентификация успешна'})
        else:
            return jsonify({'error': 'Неверный пароль'}), 401
    except Exception as e:
        app.logger.error(f'Ошибка аутентификации: {str(e)}')
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/api/auth/admin', methods=['POST'])
def api_admin_login():
    """API endpoint для аутентификации администратора"""
    try:
        data = request.json
        if not data or not data.get('password'):
            return jsonify({'error': 'Пароль обязателен'}), 400
        
        # Проверяем пароль администратора
        admin_password = os.environ.get('ADMIN_PASSWORD', 'Blalala2')
        if data['password'] == admin_password:
            return jsonify({'success': True, 'message': 'Аутентификация администратора успешна'})
        else:
            return jsonify({'error': 'Неверный пароль администратора'}), 401
    except Exception as e:
        app.logger.error(f'Ошибка аутентификации администратора: {str(e)}')
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/api/orders', methods=['GET'])
def get_orders():
    """Возвращает список ордеров с фильтрами, включая отдел."""
    employee_id = request.args.get('employee_id')
    platform = request.args.get('platform')
    status = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    department = request.args.get('department')
    query = Order.query
    if employee_id:
        query = query.filter(Order.employee_id == int(employee_id))
    if platform:
        query = query.filter(Order.platform == platform)
    else:
        query = query.filter(Order.platform != 'bybit_btc')
    if status:
        query = query.filter(Order.status == status)
    if start_date:
        query = query.filter(Order.executed_at >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        end_date_plus_one = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        query = query.filter(Order.executed_at < end_date_plus_one)
    if department:
        # join с ShiftReport для фильтрации по отделу
        query = query.join(ShiftReport, (ShiftReport.shift_date == func.date(Order.executed_at)) & (ShiftReport.employee_id == Order.employee_id)).filter(ShiftReport.department == department)
    # Сортировка по дате выполнения (новые сначала)
    query = query.order_by(Order.executed_at.desc())
    
    orders = query.all()
    
    return jsonify([{
        'id': o.id,
        'order_id': o.order_id,
        'employee_id': o.employee_id,
        'employee_name': o.employee.name if o.employee else '',
        'platform': o.platform,
        'account_name': o.account_name,
        'symbol': o.symbol,
        'side': o.side,
        'quantity': float(o.quantity),
        'price': float(o.price),
        'total_usdt': float(o.total_usdt),
        'fees_usdt': float(o.fees_usdt),
        'status': o.status,
        'executed_at': o.executed_at.isoformat(),
        'created_at': o.created_at.isoformat()
    } for o in orders])

@app.route('/api/orders/btc', methods=['GET'])
def get_btc_orders():
    """Возвращает список BTC ордеров с фильтрами (отдельная вкладка)"""
    employee_id = request.args.get('employee_id')
    status = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Получаем только ордера с платформы bybit_btc
    query = Order.query.filter(Order.platform == 'bybit_btc')
    
    if employee_id:
        query = query.filter(Order.employee_id == int(employee_id))
    if status:
        query = query.filter(Order.status == status)
    if start_date:
        query = query.filter(Order.executed_at >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        # Добавляем один день к end_date и используем строгое сравнение для включения всего дня
        end_date_plus_one = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        query = query.filter(Order.executed_at < end_date_plus_one)
    
    # Сортировка по дате выполнения (новые сначала)
    query = query.order_by(Order.executed_at.desc())
    
    orders = query.all()
    
    return jsonify([{
        'id': o.id,
        'order_id': o.order_id,
        'employee_id': o.employee_id,
        'employee_name': o.employee.name if o.employee else '',
        'platform': 'bybit_btc',  # Показываем как bybit_btc для интерфейса
        'account_name': o.account_name,
        'symbol': o.symbol,
        'side': o.side,
        'quantity': float(o.quantity),
        'price': float(o.price),
        'total_usdt': float(o.total_usdt),
        'fees_usdt': float(o.fees_usdt),
        'status': o.status,
        'executed_at': o.executed_at.isoformat(),
        'created_at': o.created_at.isoformat()
    } for o in orders])

@app.route('/api/orders', methods=['POST'])
def create_order():
    """Создает новый ордер от расширения Bybit"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Нет данных'}), 400
        
        # Валидация обязательных полей
        required_fields = ['order_id', 'employee_id', 'symbol', 'side', 'quantity', 'price']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Отсутствует обязательное поле: {field}'}), 400
        
        # Проверяем, что сотрудник существует
        employee = db.session.get(Employee, data['employee_id'])
        if not employee:
            return jsonify({'error': 'Сотрудник не найден'}), 404
        
        # Проверяем, что ордер еще не существует
        existing_order = Order.query.filter_by(order_id=data['order_id']).first()
        if existing_order:
            return jsonify({'error': 'Ордер уже существует'}), 409
        
        # Создаем ордер с данными пользователя как есть (без автовычислений)
        order = Order(
            order_id=data['order_id'],
            employee_id=data['employee_id'],
            platform=data.get('platform', 'bybit'),
            account_name=data.get('account_name', ''),
            symbol=data['symbol'],
            side=data['side'],
            quantity=float(data['quantity']),
            price=float(data['price']),
            total_usdt=float(data['total_usdt']),  # Используем значение, введенное пользователем
            fees_usdt=float(data.get('fees_usdt', 0)),
            status=data.get('status', 'filled'),
            count_in_sales=data.get('count_in_sales', False),
            count_in_purchases=data.get('count_in_purchases', False),
            executed_at=datetime.fromisoformat(data['executed_at']) if data.get('executed_at') else datetime.utcnow()
        )
        
        db.session.add(order)
        db.session.commit()
        
        return jsonify({
            'id': order.id,
            'message': 'Ордер успешно создан'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка создания ордера: {str(e)}'}), 500

@app.route('/api/orders/<int:order_id>', methods=['PUT'])
def update_order(order_id):
    """Обновляет ордер"""
    try:
        data = request.json
        print(f"DEBUG: Обновление ордера {order_id}")
        print(f"DEBUG: Полученные данные: {data}")
        
        order = db.session.get(Order, order_id)
        
        if not order:
            print(f"DEBUG: Ордер {order_id} не найден")
            return jsonify({'error': 'Ордер не найден'}), 404
        
        print(f"DEBUG: Текущий ордер: order_id={order.order_id}, platform={order.platform}, symbol={order.symbol}")
        
        # Обновляем все разрешенные поля
        if 'order_id' in data:
            # Проверяем, что новый order_id не конфликтует с существующим
            existing_order = Order.query.filter_by(order_id=data['order_id']).first()
            if existing_order and existing_order.id != order_id:
                print(f"DEBUG: Конфликт order_id: {data['order_id']}")
                return jsonify({'error': 'Ордер с таким ID уже существует'}), 409
            print(f"DEBUG: Обновляем order_id с '{order.order_id}' на '{data['order_id']}'")
            order.order_id = data['order_id']
        
        if 'employee_id' in data:
            # Проверяем, что сотрудник существует
            employee = db.session.get(Employee, data['employee_id'])
            if not employee:
                print(f"DEBUG: Сотрудник {data['employee_id']} не найден")
                return jsonify({'error': 'Сотрудник не найден'}), 404
            print(f"DEBUG: Обновляем employee_id с {order.employee_id} на {data['employee_id']}")
            order.employee_id = data['employee_id']
        
        if 'platform' in data:
            print(f"DEBUG: Обновляем platform с '{order.platform}' на '{data['platform']}'")
            order.platform = data['platform']
        
        if 'account_name' in data:
            print(f"DEBUG: Обновляем account_name с '{order.account_name}' на '{data['account_name']}'")
            order.account_name = data['account_name']
        
        if 'symbol' in data:
            print(f"DEBUG: Обновляем symbol с '{order.symbol}' на '{data['symbol']}'")
            order.symbol = data['symbol']
        
        if 'side' in data:
            print(f"DEBUG: Обновляем side с '{order.side}' на '{data['side']}'")
            order.side = data['side']
        
        if 'quantity' in data:
            print(f"DEBUG: Обновляем quantity с {order.quantity} на {data['quantity']}")
            order.quantity = float(data['quantity'])
        
        if 'price' in data:
            print(f"DEBUG: Обновляем price с {order.price} на {data['price']}")
            order.price = float(data['price'])
        
        if 'total_usdt' in data:
            print(f"DEBUG: Обновляем total_usdt с {order.total_usdt} на {data['total_usdt']}")
            order.total_usdt = float(data['total_usdt'])
        
        if 'fees_usdt' in data:
            print(f"DEBUG: Обновляем fees_usdt с {order.fees_usdt} на {data['fees_usdt']}")
            order.fees_usdt = float(data['fees_usdt'])
        
        if 'status' in data:
            print(f"DEBUG: Обновляем status с '{order.status}' на '{data['status']}'")
            order.status = data['status']
        
        if 'executed_at' in data:
            print(f"DEBUG: Обновляем executed_at с {order.executed_at} на {data['executed_at']}")
            order.executed_at = datetime.fromisoformat(data['executed_at'])
        
        if 'count_in_sales' in data:
            print(f"DEBUG: Обновляем count_in_sales с {order.count_in_sales} на {data['count_in_sales']}")
            order.count_in_sales = data['count_in_sales']
        
        if 'count_in_purchases' in data:
            print(f"DEBUG: Обновляем count_in_purchases с {order.count_in_purchases} на {data['count_in_purchases']}")
            order.count_in_purchases = data['count_in_purchases']
        
        # Обновляем время изменения
        order.updated_at = datetime.utcnow()
        
        print(f"DEBUG: Сохраняем изменения в базу данных...")
        db.session.commit()
        
        print(f"DEBUG: Ордер успешно обновлен")
        return jsonify({'message': 'Ордер успешно обновлен'})
        
    except Exception as e:
        print(f"DEBUG: Ошибка обновления ордера: {str(e)}")
        db.session.rollback()
        return jsonify({'error': f'Ошибка обновления ордера: {str(e)}'}), 500

@app.route('/api/orders/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    """Удаляет ордер"""
    try:
        data = request.get_json()
        if not validate_admin_password(data):
            return jsonify({'error': 'Неверный пароль'}), 403
        
        order = db.session.get(Order, order_id)
        if not order:
            return jsonify({'error': 'Ордер не найден'}), 404
        
        db.session.delete(order)
        db.session.commit()
        
        return jsonify({'message': 'Ордер удален'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка удаления ордера: {str(e)}'}), 500

@app.route('/api/orders/bulk-delete', methods=['POST'])
def bulk_delete_orders():
    """Массовое удаление ордеров с проверкой пароля"""
    try:
        data = request.get_json()
        
        # Проверяем пароль администратора
        if not validate_admin_password(data):
            return jsonify({'error': 'Неверный пароль администратора'}), 403
        
        order_ids = data.get('order_ids', [])
        
        if not order_ids:
            return jsonify({'error': 'Не указаны ID ордеров для удаления'}), 400
        
        # Находим все ордеры для удаления
        orders_to_delete = Order.query.filter(Order.id.in_(order_ids)).all()
        
        if not orders_to_delete:
            return jsonify({'error': 'Ордеры не найдены'}), 404
        
        # Удаляем ордеры
        for order in orders_to_delete:
            db.session.delete(order)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'deleted_count': len(orders_to_delete),
            'message': f'Успешно удалено {len(orders_to_delete)} ордеров'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка при массовом удалении: {str(e)}'}), 500

@app.route('/api/orders/statistics', methods=['GET'])
def get_orders_statistics():
    """Возвращает статистику по ордерам"""
    employee_id = request.args.get('employee_id')
    platform = request.args.get('platform')
    status = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    exclude_canceled = request.args.get('exclude_canceled', 'true').lower() == 'true'  # По умолчанию исключаем отмененные
    
    query = Order.query
    
    if employee_id:
        query = query.filter(Order.employee_id == int(employee_id))
    if platform:
        if platform == 'bybit_btc':
            # Для BTC показываем только BTC-ордера
            query = query.filter(Order.platform == 'bybit_btc')
        else:
            # Для остальных платформ (bybit, gate, bliss, htx) показываем общую статистику
            # включаем все платформы кроме BTC
            query = query.filter(Order.platform != 'bybit_btc')
    else:
        # Общая статистика: включаем все платформы кроме BTC
        query = query.filter(Order.platform != 'bybit_btc')
    if status:
        query = query.filter(Order.status == status)
    elif exclude_canceled:
        # Если статус не указан явно, исключаем отмененные и неуспешные ордера
        query = query.filter(~Order.status.in_(['canceled', 'expired', 'failed']))
    if start_date:
        query = query.filter(Order.executed_at >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        # Добавляем один день к end_date и используем строгое сравнение для включения всего дня
        end_date_plus_one = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        query = query.filter(Order.executed_at < end_date_plus_one)
    
    orders = query.all()
    
    # Если выбрана вкладка BTC, считаем отдельную сумму USDT по BTC-ордерам
    btc_total_usdt = None
    if platform == 'bybit_btc':
        btc_total_usdt = sum(float(o.quantity) for o in orders)
    
    # Статистика
    total_orders = len(orders)
    total_volume_rub = sum(float(o.total_usdt) for o in orders)  # Общий объем RUB
    total_volume_usdt = sum(float(o.quantity) for o in orders)  # Общий объем USDT
    total_fees = sum(float(o.fees_usdt) for o in orders)
    
    # Статистика по статусам
    status_stats = {}
    for order in orders:
        status = order.status
        if status not in status_stats:
            status_stats[status] = 0
        status_stats[status] += 1
    
    # Статистика по сторонам (buy/sell) - используем только завершенные ордера
    completed_orders = [o for o in orders if o.status == 'filled']
    buy_orders = [o for o in completed_orders if o.side == 'buy']
    sell_orders = [o for o in completed_orders if o.side == 'sell']
    
    # Расчет объемов только для завершенных ордеров
    buy_volume_rub = sum(float(o.total_usdt) for o in buy_orders)    # Сумма RUB для покупок
    sell_volume_rub = sum(float(o.total_usdt) for o in sell_orders)  # Сумма RUB для продаж
    buy_volume_usdt = sum(float(o.quantity) for o in buy_orders)     # Сумма USDT для покупок
    sell_volume_usdt = sum(float(o.quantity) for o in sell_orders)   # Сумма USDT для продаж
    
    # Инициализируем переменную special_orders и заполняем её
    special_statuses = ['dokidka', 'internal_transfer', 'appealed', 'scam']
    special_orders_query = Order.query.filter(Order.status.in_(special_statuses))
    
    # Применяем фильтры по датам только если они указаны
    if start_date:
        special_orders_query = special_orders_query.filter(Order.executed_at >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        # Добавляем один день к end_date и используем строгое сравнение для включения всего дня
        end_date_plus_one = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        special_orders_query = special_orders_query.filter(Order.executed_at < end_date_plus_one)
    
    # Если указан employee_id, фильтруем по сотруднику
    if employee_id:
        special_orders_query = special_orders_query.filter(Order.employee_id == int(employee_id))
    
    # Применяем те же фильтры по платформе, что и для обычных ордеров
    if platform:
        if platform == 'bybit_btc':
            # Для BTC показываем только BTC-ордера
            special_orders_query = special_orders_query.filter(Order.platform == 'bybit_btc')
        else:
            # Для остальных платформ (bybit, gate, bliss, htx) показываем общую статистику
            # включаем все платформы кроме BTC
            special_orders_query = special_orders_query.filter(Order.platform != 'bybit_btc')
    else:
        # Общая статистика: включаем все платформы кроме BTC
        special_orders_query = special_orders_query.filter(Order.platform != 'bybit_btc')
    
    special_orders = special_orders_query.all()
    
    # Добавляем покупки из специальных ордеров (с учетом чекбоксов)
    special_buys_rub = 0
    special_buys_usdt = 0
    
    for order in special_orders:
        if order.count_in_purchases:
            order_amount_rub = float(order.total_usdt or 0)
            order_amount_usdt = float(order.quantity or 0)
            
            if order.status == 'scam':
                # Скам добавляем к покупкам
                special_buys_rub += order_amount_rub
                special_buys_usdt += order_amount_usdt
            else:
                # Остальные добавляем к покупкам
                special_buys_rub += order_amount_rub
                special_buys_usdt += order_amount_usdt
    
    # Общие покупки по формуле
    total_buys_rub = buy_volume_rub + special_buys_rub
    total_buys_usdt = buy_volume_usdt + special_buys_usdt
    
    # Расчет среднего курса для завершенных ордеров
    avg_buy_rate = buy_volume_rub / buy_volume_usdt if buy_volume_usdt > 0 else 0
    avg_sell_rate = sell_volume_rub / sell_volume_usdt if sell_volume_usdt > 0 else 0
    
    # Получаем значения докидки, внутреннего перевода и скама из отчетов
    dokidka_amount = 0
    internal_transfer_amount = 0
    scam_amount = 0
    
    # Получаем данные из отчетов за указанный период (всех сотрудников или конкретного)
    if employee_id:
        # Если указан employee_id, получаем отчеты только этого сотрудника
        employee_reports_query = ShiftReport.query.filter(ShiftReport.employee_id == employee_id)
    else:
        # Если employee_id не указан, получаем отчеты всех сотрудников за период
        employee_reports_query = ShiftReport.query
    
    # Применяем фильтры по датам только если они указаны
    if start_date:
        employee_reports_query = employee_reports_query.filter(ShiftReport.shift_date >= start_date)
    if end_date:
        employee_reports_query = employee_reports_query.filter(ShiftReport.shift_date <= end_date)
    
    employee_reports = employee_reports_query.all()
    
    # Суммируем докидки, внутренние переводы и скамы из отчетов
    for report in employee_reports:
        dokidka_amount += float(report.dokidka_amount or 0)
        internal_transfer_amount += float(report.internal_transfer_amount or 0)
        scam_amount += float(report.scam_amount or 0)
    
    # Суммируем суммы из ордеров с учетом чекбоксов
    for order in special_orders:
        order_amount = float(order.quantity or 0)
        
        # Учитываем в продажах если помечено
        if order.count_in_sales:
            if order.status == 'scam':
                # Скам добавляем к продажам
                scam_amount += order_amount
            else:
                # Остальные добавляем к продажам
                dokidka_amount += order_amount
        
        # Учитываем в покупках если помечено
        if order.count_in_purchases:
            if order.status == 'scam':
                # Скам добавляем к покупкам
                scam_amount += order_amount
            else:
                # Остальные добавляем к покупкам
                internal_transfer_amount += order_amount
    
    # Добавляем докидки и внутренние переводы к общим продажам, вычитаем скам
    total_sales_with_transfers = sell_volume_usdt + dokidka_amount + internal_transfer_amount - scam_amount
    
    # Обычные продажи (завершенные)
    sell_volume_rub = sum(float(o.total_usdt) for o in sell_orders)
    sell_volume_usdt = sum(float(o.quantity) for o in sell_orders)

    # Продажи из специальных ордеров (с учетом чекбоксов)
    special_sales_rub = 0
    special_sales_usdt = 0
    
    for order in special_orders:
        if order.count_in_sales:
            order_amount_rub = float(order.total_usdt or 0)
            order_amount_usdt = float(order.quantity or 0)
            
            if order.status == 'scam':
                # Скам добавляем к продажам
                special_sales_rub += order_amount_rub
                special_sales_usdt += order_amount_usdt
            else:
                # Остальные добавляем к продажам
                special_sales_rub += order_amount_rub
                special_sales_usdt += order_amount_usdt

    # Общие продажи по формуле
    total_sales_rub = sell_volume_rub + special_sales_rub
    total_sales_usdt = sell_volume_usdt + special_sales_usdt

    # Рассчитываем прибыль в USDT (покупки - продажи с учетом переводов и скама)
    profit_usdt = total_buys_usdt - total_sales_usdt

    # Рассчитываем прибыль в рублях (покупки - продажи с учетом переводов и скама)
    profit_rub = total_buys_rub - total_sales_rub

    # Отладочная информация
    print(f"DEBUG STATS: buy_volume_rub={buy_volume_rub}, special_buys_rub={special_buys_rub}")
    print(f"DEBUG STATS: buy_volume_usdt={buy_volume_usdt}, special_buys_usdt={special_buys_usdt}")
    print(f"DEBUG STATS: total_buys_rub={total_buys_rub}, total_buys_usdt={total_buys_usdt}")
    print(f"DEBUG STATS: sell_volume_rub={sell_volume_rub}, special_sales_rub={special_sales_rub}")
    print(f"DEBUG STATS: sell_volume_usdt={sell_volume_usdt}, special_sales_usdt={special_sales_usdt}")
    print(f"DEBUG STATS: total_sales_rub={total_sales_rub}, total_sales_usdt={total_sales_usdt}")
    
    # --- ДЕТАЛЬНАЯ ОТЛАДКА ДЛЯ ВЫЯВЛЕНИЯ УДВОЕНИЯ USDT ---
    print("\n=== ДЕТАЛЬНАЯ ОТЛАДКА СТАТИСТИКИ ===")
    
    # Получаем все ордера продаж с нужными статусами
    sales_statuses = ['filled', 'dokidka', 'appealed']
    all_sell_orders_query = Order.query.filter(Order.side == 'sell').filter(Order.status.in_(sales_statuses))
    
    # Применяем фильтры по датам
    if start_date:
        all_sell_orders_query = all_sell_orders_query.filter(Order.executed_at >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        end_date_plus_one = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        all_sell_orders_query = all_sell_orders_query.filter(Order.executed_at < end_date_plus_one)
    
    # Применяем фильтр по сотруднику
    if employee_id:
        all_sell_orders_query = all_sell_orders_query.filter(Order.employee_id == int(employee_id))
    
    all_sell_orders = all_sell_orders_query.all()

    print(f"DEBUG: Найдено {len(all_sell_orders)} ордеров продаж со статусами {sales_statuses}")
    print(f"DEBUG: Фильтры: employee_id={employee_id}, start_date={start_date}, end_date={end_date}")
    
    # Проверяем на дубликаты
    order_ids = [o.order_id for o in all_sell_orders]
    unique_order_ids = set(order_ids)
    print(f"DEBUG: Уникальных order_id: {len(unique_order_ids)} из {len(order_ids)}")
    
    if len(order_ids) != len(unique_order_ids):
        print("DEBUG: ВНИМАНИЕ! Обнаружены дубликаты ордеров!")
        from collections import Counter
        duplicates = Counter(order_ids)
        for order_id, count in duplicates.items():
            if count > 1:
                print(f"DEBUG: Дубликат order_id={order_id} встречается {count} раз")
    
    # Подсчитываем суммы по статусам
    status_totals = {}
    for order in all_sell_orders:
        status = order.status
        if status not in status_totals:
            status_totals[status] = {'rub': 0, 'usdt': 0, 'count': 0}
        status_totals[status]['rub'] += float(order.total_usdt or 0)
        status_totals[status]['usdt'] += float(order.quantity or 0)
        status_totals[status]['count'] += 1
    
    print("DEBUG: Суммы по статусам:")
    for status, totals in status_totals.items():
        print(f"DEBUG: {status}: RUB={totals['rub']:.2f}, USDT={totals['usdt']:.2f}, count={totals['count']}")
    
    print(f"DEBUG: Итоговые суммы:")
    print(f"DEBUG: total_sales_rub = {total_sales_rub:.2f}")
    print(f"DEBUG: total_sales_usdt = {total_sales_usdt:.2f}")
    print(f"DEBUG: scam_amount = {scam_amount}")
    print("=== КОНЕЦ ОТЛАДКИ ===\n")

    return jsonify({
        'total_orders': total_orders,
        'status_stats': status_stats,
        'sell_volume': round(total_sales_rub, 2),
        'buy_volume': round(total_buys_rub, 2),
        'sell_volume_usdt': round(total_sales_usdt, 2),
        'buy_volume_usdt': round(total_buys_usdt, 2),
        'avg_sell_rate': round(avg_sell_rate, 2),
        'avg_buy_rate': round(avg_buy_rate, 2),
        'profit_usdt': round(profit_usdt, 2),
        'profit_rub': round(profit_rub, 2),
        'dokidka_amount': round(dokidka_amount, 2),
        'internal_transfer_amount': round(internal_transfer_amount, 2),
        'scam_amount': round(scam_amount, 2),
        'total_volume_rub': round(total_volume_rub, 2),
        'total_volume_usdt': round(total_volume_usdt, 2),
        'btc_total_usdt': btc_total_usdt
    })

@app.route('/api/orders/upload', methods=['POST'])
def upload_orders():
    """Загружает ордера из файла Excel/CSV с фильтрацией по времени"""
    try:
        # Проверяем обязательные поля
        employee_id = request.form.get('employee_id')
        platform = request.form.get('platform')
        account_name = request.form.get('account_name')
        
        if not employee_id or not platform or not account_name:
            return jsonify({'error': 'Не указаны обязательные поля'}), 400
        
        # Получаем параметры фильтрации по времени
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        
        print(f"\nDEBUG UPLOAD: Параметры запроса:")
        print(f"DEBUG UPLOAD: employee_id = {employee_id}")
        print(f"DEBUG UPLOAD: platform = {platform}")
        print(f"DEBUG UPLOAD: account_name = {account_name}")
        print(f"DEBUG UPLOAD: start_date_str = {start_date_str}")
        print(f"DEBUG UPLOAD: end_date_str = {end_date_str}")
        
        start_date = None
        end_date = None
        
        # Парсим начальную дату
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
                print(f"DEBUG UPLOAD: start_date = {start_date}")
            except ValueError:
                return jsonify({'error': 'Неверный формат начальной даты'}), 400
        
        # Парсим конечную дату
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')
                print(f"DEBUG UPLOAD: end_date = {end_date}")
            except ValueError:
                return jsonify({'error': 'Неверный формат конечной даты'}), 400
        
        # Проверяем логику дат
        if start_date and end_date and start_date > end_date:
            return jsonify({'error': 'Начальная дата не может быть больше конечной'}), 400
        
        # Проверяем, что сотрудник существует
        employee = db.session.get(Employee, employee_id)
        if not employee:
            return jsonify({'error': 'Сотрудник не найден'}), 404
        
        # Проверяем файл
        if 'file' not in request.files:
            return jsonify({'error': 'Файл не загружен'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Файл не выбран'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Неподдерживаемый тип файла'}), 400
        
        # Сохраняем файл с правильным расширением
        original_filename = file.filename or 'upload.xlsx'
        # Определяем расширение из оригинального имени файла
        file_ext = os.path.splitext(original_filename)[1].lower()
        if not file_ext:
            file_ext = '.xlsx'  # По умолчанию
        
        # Создаем безопасное имя файла, сохраняя расширение
        safe_name = secure_filename(original_filename)
        if not safe_name or len(safe_name) < 3:
            safe_name = f"upload{file_ext}"
        else:
            # Если secure_filename удалил все символы кроме расширения, добавляем имя по умолчанию
            base_name = os.path.splitext(safe_name)[0]
            if not base_name or len(base_name) < 1:
                safe_name = f"upload{file_ext}"
            elif not safe_name.endswith(file_ext):
                # Если расширение потерялось, добавляем его
                safe_name = f"{base_name}{file_ext}"
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{safe_name}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        print(f"DEBUG UPLOAD: Сохраняем файл: {filepath}")
        file.save(filepath)
        
        # Обрабатываем файл с фильтрацией по времени, передаем оригинальное имя для определения типа
        orders_data = parse_orders_file(filepath, platform, start_date, end_date, original_filename)
        print(f"DEBUG UPLOAD: Получено {len(orders_data)} ордеров из файла")
        
        # Сохраняем ордера в базу данных
        created_orders = []
        skipped_orders = []
        
        for order_data in orders_data:
            # Проверяем, что ордер еще не существует
            existing_order = Order.query.filter_by(
                order_id=order_data['order_id'],
                platform=platform
            ).first()
            if existing_order:
                skipped_orders.append(order_data['order_id'])
                continue
            
            # Создаем новый ордер
            order = Order(
                order_id=order_data['order_id'],
                employee_id=employee_id,
                platform=platform,
                account_name=order_data.get('account_name') or account_name,  # Используем account_name из order_data, если есть
                symbol=order_data['symbol'],
                side=order_data['side'],
                quantity=order_data['quantity'],
                price=order_data['price'],
                total_usdt=order_data['total_usdt'],
                fees_usdt=order_data.get('fees_usdt', 0),
                status=order_data.get('status', 'filled'),
                executed_at=order_data['executed_at']
            )
            
            db.session.add(order)
            created_orders.append(order_data['order_id'])
            print(f"DEBUG UPLOAD: Создан ордер {order_data['order_id']}")
        
        db.session.commit()
        
        # Формируем сообщение о результате
        message = f'Загружено {len(created_orders)} ордеров, пропущено {len(skipped_orders)} дублей'
        if start_date or end_date:
            total_parsed = len(orders_data)
            message += f', обработано {total_parsed} ордеров из файла'
            if start_date:
                message += f' с {start_date.strftime("%d.%m.%Y %H:%M")}'
            if end_date:
                message += f' по {end_date.strftime("%d.%m.%Y %H:%M")}'
        
        return jsonify({
            'success': True,
            'count': len(created_orders),
            'skipped': len(skipped_orders),
            'total_parsed': len(orders_data),
            'message': message
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка обработки файла: {str(e)}'}), 500

@app.route('/api/platform-balances', methods=['GET'])
def get_platform_balances():
    """Возвращает текущие балансы по всем площадкам"""
    try:
        # Получаем все отчеты, отсортированные по дате и ID
        all_reports = ShiftReport.query.order_by(
            ShiftReport.shift_date.desc(), 
            ShiftReport.id.desc()
        ).all()
        
        if not all_reports:
            return jsonify({
                'platforms': [],
                'total_balance': 0,
                'active_platforms_count': 0,
                'last_update': None,
                'message': 'Нет данных о балансах'
            })
        
        # Собираем последние балансы для каждого аккаунта
        account_balances = {}  # {platform: {account_name: {balance, last_update_info}}}
        
        for report in all_reports:
            try:
                balances = json.loads(report.balances_json or '{}')
            except json.JSONDecodeError:
                continue
                
            employee = db.session.get(Employee, report.employee_id)
            employee_name = employee.name if employee else 'Неизвестный сотрудник'
            
            for platform in ['bybit', 'htx', 'bliss', 'gate']:
                if platform not in account_balances:
                    account_balances[platform] = {}
                    
                platform_accounts = balances.get(platform, [])
                for acc in platform_accounts:
                    account_name = acc.get('account_name', 'Неизвестный аккаунт')
                    
                    # Если для этого аккаунта ещё нет записи, добавляем её
                    if account_name not in account_balances[platform]:
                        try:
                            balance_str = acc.get('end_balance', '0')
                            balance = float(balance_str) if balance_str and balance_str != '' else 0.0
                        except (ValueError, TypeError):
                            balance = 0.0
                            
                        account_balances[platform][account_name] = {
                            'balance': balance,
                            'account_id': acc.get('account_id') or acc.get('id'),
                            'last_update': {
                                'date': report.shift_date.isoformat(),
                                'shift_type': report.shift_type,
                                'employee_name': employee_name
                            }
                        }
        
        # Формируем результат
        platform_stats = []
        total_balance = 0
        active_platforms_count = 0
        latest_update = None
        
        for platform in ['bybit', 'htx', 'bliss', 'gate']:
            platform_accounts = account_balances.get(platform, {})
            platform_total = 0
            accounts_data = []
            
            for account_name, account_info in platform_accounts.items():
                balance = account_info['balance']
                platform_total += balance
                accounts_data.append({
                    'account_id': account_info['account_id'],
                    'account_name': account_name,
                    'balance': round(balance, 2),
                    'last_update': account_info['last_update']
                })
            
            total_balance += platform_total
            
            # Считаем площадку активной, если у неё есть аккаунты
            if len(platform_accounts) > 0:
                active_platforms_count += 1
            
            platform_stats.append({
                'platform': platform,
                'platform_name': {
                    'bybit': 'Bybit',
                    'htx': 'HTX',
                    'bliss': 'Bliss',
                    'gate': 'Gate'
                }.get(platform, platform.upper()),
                'total_balance': round(platform_total, 2),
                'accounts_count': len(platform_accounts),
                'accounts': accounts_data
            })
        
        # Информация о последнем обновлении (из самого свежего отчета)
        latest_report = all_reports[0]
        latest_employee = db.session.get(Employee, latest_report.employee_id)
        
        return jsonify({
            'platforms': platform_stats,
            'total_balance': round(total_balance, 2),
            'active_platforms_count': active_platforms_count,
            'last_update': {
                'date': latest_report.shift_date.isoformat(),
                'shift_type': latest_report.shift_type,
                'employee_name': latest_employee.name if latest_employee else 'Неизвестный сотрудник',
                'updated_at': latest_report.updated_at.isoformat() if latest_report.updated_at else None
            }
        })
        
    except Exception as e:
        app.logger.error(f'Ошибка при получении балансов площадок: {str(e)}')
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/api/employee-profile/<int:employee_id>', methods=['GET'])
def get_employee_profile(employee_id):
    """Возвращает детальный профиль сотрудника с максимальным количеством показателей"""
    try:
        # Получаем параметры фильтрации
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date or not end_date:
            today = datetime.now().date()
            start_date = today.replace(day=1)
            end_date = today
        else:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        print(f"[SEARCH] Ищем отчеты за период: {start_date} - {end_date}")
        
        # Получаем сотрудника
        employee = Employee.query.get_or_404(employee_id)
        
        # Сначала проверим все отчеты этого сотрудника
        all_reports = ShiftReport.query.filter(
            ShiftReport.employee_id == employee_id
        ).order_by(ShiftReport.shift_date.desc()).all()
        
        # Получаем все отчеты сотрудника за период
        reports = ShiftReport.query.filter(
            ShiftReport.employee_id == employee_id,
            ShiftReport.shift_date >= start_date,
            ShiftReport.shift_date <= end_date
        ).order_by(ShiftReport.shift_date.desc()).all()
        
        # Отладочная информация
        print(f"[PROFILE] Профиль сотрудника {employee.name} (ID: {employee_id})")
        print(f"[PERIOD] Период: {start_date} - {end_date}")
        print(f"[STATS] Всего отчетов у сотрудника: {len(all_reports)}")
        if all_reports:
            print("[LIST] Все отчеты сотрудника:")
            for r in all_reports:
                print(f"   - {r.shift_date} ({r.shift_type}) - {r.total_requests} заявок")
        print(f"[STATS] Найдено отчетов за период: {len(reports)}")
        for i, report in enumerate(reports):
            print(f"  [LIST] Отчет {i+1}: {report.shift_date} ({report.shift_type})")
            print(f"    Всего заявок: {report.total_requests}")
            print(f"    Bybit: {report.bybit_requests}, HTX: {report.htx_requests}, Bliss: {report.bliss_requests}")
            print(f"    Балансы JSON: {report.balances_json[:100]}...")
            profit_data = calculate_profit_from_orders(db.session, report)
            print(f"    Прибыль: {profit_data}")
            print(f"    Скам: {report.scam_amount}, Докидка: {report.dokidka_amount}")
            print("    ---")
        
        # Автоматически привязываем ордера к отчетам сотрудника
        from utils import link_orders_to_employee
        total_linked = 0
        for report in reports:
            if report.shift_start_time and report.shift_end_time:
                linked_count = link_orders_to_employee(db.session, report)
                total_linked += linked_count
                if linked_count > 0:
                    print(f"[LINK] Привязано {linked_count} ордеров к отчету от {report.shift_date}")
        
        if total_linked > 0:
            print(f"[LINK] Всего привязано {total_linked} ордеров к отчетам сотрудника")
        
        # Получаем все ордера сотрудника за период
        orders = Order.query.filter(
            Order.employee_id == employee_id,
            Order.executed_at >= datetime.combine(start_date, datetime.min.time()),
            Order.executed_at < datetime.combine(end_date + timedelta(days=1), datetime.min.time())
        ).all()
        
        print("[WORK] Начинаем расчет основной статистики...")
        try:
            # Основная статистика
            basic_stats = calculate_employee_statistics(reports, employee, db)
            print(f"[OK] Основная статистика: {basic_stats}")
        except Exception as e:
            print(f"[ERROR] Ошибка при расчете основной статистики: {str(e)}")
            import traceback
            traceback.print_exc()
            basic_stats = {}
        
        print("[WORK] Начинаем расчет детальной статистики по отчетам...")
        # Детальная статистика по отчетам
        report_details = []
        total_project_profit = 0
        total_salary_profit = 0
        platform_profits = {'bybit': 0, 'htx': 0, 'bliss': 0, 'gate': 0}
        
        for i, report in enumerate(reports):
            print(f"[WORK] Обрабатываем отчет {i+1}/{len(reports)}: {report.shift_date}")
            try:
                profit_data = calculate_profit_from_orders(db.session, report)
                print(f"[OK] Прибыль рассчитана: {profit_data}")
                total_project_profit += profit_data['project_profit']
                total_salary_profit += profit_data['salary_profit']
            except Exception as e:
                print(f"[ERROR] Ошибка при расчете прибыли для отчета {report.shift_date}: {str(e)}")
                import traceback
                traceback.print_exc()
                profit_data = {'project_profit': 0, 'salary_profit': 0, 'profit': 0, 'scam': 0, 'dokidka': 0, 'internal': 0}
            
            # Парсим балансы
            print(f"[WORK] Парсим балансы для отчета {report.shift_date}...")
            try:
                balances = json.loads(report.balances_json or '{}')
                print(f"[OK] Балансы распарсены: {len(balances)} платформ")
            except Exception as e:
                print(f"[ERROR] Ошибка при парсинге балансов: {str(e)}")
                balances = {}
            
            # Считаем прибыль по платформам
            print(f"[WORK] Считаем прибыль по платформам...")
            platform_deltas = {}
            try:
                for platform in ['bybit', 'htx', 'bliss', 'gate']:
                    accounts_list = balances.get(platform, [])
                    delta = 0
                    for acc in accounts_list:
                        prev = find_prev_balance(db.session, acc.get('account_id') or acc.get('id'), platform, report)
                        cur = float(acc.get('balance', 0)) if acc.get('balance') not in (None, '') else 0
                        delta += cur - prev
                    platform_deltas[platform] = delta
                    platform_profits[platform] += delta
                print(f"[OK] Прибыль по платформам рассчитана: {platform_deltas}")
            except Exception as e:
                print(f"[ERROR] Ошибка при расчете прибыли по платформам: {str(e)}")
                import traceback
                traceback.print_exc()
                platform_deltas = {'bybit': 0, 'htx': 0, 'bliss': 0, 'gate': 0}
            
            print(f"[WORK] Формируем детали отчета...")
            try:
                report_details.append({
                    'id': report.id,
                    'date': report.shift_date.isoformat(),
                    'shift_type': report.shift_type,
                    'total_requests': report.total_requests,
                    'bybit_requests': report.bybit_requests or 0,
                    'htx_requests': report.htx_requests or 0,
                    'bliss_requests': report.bliss_requests or 0,
                    'project_profit': round(profit_data['project_profit'], 2),
                    'salary_profit': round(profit_data['salary_profit'], 2),
                    'scam_amount': float(report.scam_amount or 0),

                    'dokidka_amount': float(report.dokidka_amount or 0),
                    'internal_transfer_amount': float(report.internal_transfer_amount or 0),
                    'platform_deltas': platform_deltas,
                    'balances': balances
                })
                print(f"[OK] Детали отчета добавлены")
            except Exception as e:
                print(f"[ERROR] Ошибка при формировании деталей отчета: {str(e)}")
                import traceback
                traceback.print_exc()
        
        print("[WORK] Начинаем расчет статистики по ордерам...")
        print(f"[WORK] Найдено ордеров: {len(orders)}")
        
        # Рассчитываем статистику на основе привязанных ордеров
        from utils import calculate_shift_stats_from_orders
        order_stats = calculate_shift_stats_from_orders(orders)
        
        # Пересчитываем прибыль используя ту же логику, что и в API статистики ордеров
        # Прибыль = покупки - продажи (из ордеров)
        # Получаем все ордера за период для данного сотрудника
        from datetime import datetime, timedelta
        
        # Получаем ордера покупок
        buy_orders = Order.query.filter(
            Order.employee_id == employee_id,
            Order.side == 'buy',
            Order.status == 'filled',
            Order.executed_at >= start_date,
            Order.executed_at <= end_date + timedelta(days=1)
        ).all()
        
        # Получаем ордера продаж
        sell_orders = Order.query.filter(
            Order.employee_id == employee_id,
            Order.side == 'sell',
            Order.status == 'filled',
            Order.executed_at >= start_date,
            Order.executed_at <= end_date + timedelta(days=1)
        ).all()
        
        # Рассчитываем суммы
        total_buys_usdt = sum(float(order.quantity) for order in buy_orders)
        total_sales_usdt = sum(float(order.quantity) for order in sell_orders)
        
        # Рассчитываем суммы в рублях
        total_buys_rub = sum(float(order.total_usdt) for order in buy_orders)
        total_sales_rub = sum(float(order.total_usdt) for order in sell_orders)
        
        # Прибыль = покупки - продажи
        profit_from_orders = total_buys_usdt - total_sales_usdt
        
        # Заменяем статистику из ордеров на правильную статистику
        order_stats.update({
            'total_purchases_usdt': round(total_buys_usdt, 2),
            'total_sales_usdt': round(total_sales_usdt, 2),
            'total_purchases_rub': round(total_buys_rub, 2),
            'total_sales_rub': round(total_sales_rub, 2),
            'profit_usdt': round(profit_from_orders, 2)
        })
        
        # Дополнительная статистика по платформам
        platform_stats = {}
        platform_detailed_stats = {}
        
        for order in orders:
            platform = order.platform
            if platform not in platform_stats:
                platform_stats[platform] = 0
                platform_detailed_stats[platform] = {
                    'total_orders': 0,
                    'buy_orders': 0,
                    'sell_orders': 0,
                    'total_buys_usdt': 0,
                    'total_sales_usdt': 0,
                    'total_buys_rub': 0,
                    'total_sales_rub': 0,
                    'avg_buy_price': 0,
                    'avg_sell_price': 0,
                    'profit_usdt': 0
                }
            
            platform_stats[platform] += 1
            platform_detailed_stats[platform]['total_orders'] += 1
            
            if order.status == 'filled':
                if order.side == 'buy':
                    platform_detailed_stats[platform]['buy_orders'] += 1
                    platform_detailed_stats[platform]['total_buys_usdt'] += float(order.quantity)
                    platform_detailed_stats[platform]['total_buys_rub'] += float(order.total_usdt)
                elif order.side == 'sell':
                    platform_detailed_stats[platform]['sell_orders'] += 1
                    platform_detailed_stats[platform]['total_sales_usdt'] += float(order.quantity)
                    platform_detailed_stats[platform]['total_sales_rub'] += float(order.total_usdt)
        
        # Рассчитываем средние цены и прибыль для каждой платформы
        for platform, stats in platform_detailed_stats.items():
            if stats['total_buys_usdt'] > 0:
                stats['avg_buy_price'] = stats['total_buys_rub'] / stats['total_buys_usdt']
            if stats['total_sales_usdt'] > 0:
                stats['avg_sell_price'] = stats['total_sales_rub'] / stats['total_sales_usdt']
            stats['profit_usdt'] = stats['total_buys_usdt'] - stats['total_sales_usdt']
            
            # Округляем значения
            stats['avg_buy_price'] = round(stats['avg_buy_price'], 2)
            stats['avg_sell_price'] = round(stats['avg_sell_price'], 2)
            stats['profit_usdt'] = round(stats['profit_usdt'], 2)
            stats['total_buys_usdt'] = round(stats['total_buys_usdt'], 2)
            stats['total_sales_usdt'] = round(stats['total_sales_usdt'], 2)
            stats['total_buys_rub'] = round(stats['total_buys_rub'], 2)
            stats['total_sales_rub'] = round(stats['total_sales_rub'], 2)
        
        # Статистика по статусам
        status_stats = {}
        for order in orders:
            status = order.status
            if status not in status_stats:
                status_stats[status] = 0
            status_stats[status] += 1
        
        # Объединяем статистику
        order_stats.update({
            'platform_stats': platform_stats,
            'platform_detailed_stats': platform_detailed_stats,
            'status_stats': status_stats,
            'total_fees': sum(float(o.fees_usdt) for o in orders),
            'total_orders_count': len(orders),
            'completed_orders_count': len([o for o in orders if o.status == 'filled']),
            'canceled_orders_count': len([o for o in orders if o.status == 'canceled']),
            'pending_orders_count': len([o for o in orders if o.status == 'pending']),
            'special_orders_count': len([o for o in orders if o.status in ['scam', 'dokidka', 'internal_transfer', 'appealed']])
        })
        
        print("[WORK] Начинаем расчет временной статистики...")
        # Временная статистика
        time_stats = {}
        try:
            if reports:
                first_report = min(reports, key=lambda r: r.shift_date)
                last_report = max(reports, key=lambda r: r.shift_date)
                
                time_stats = {
                    'first_report_date': first_report.shift_date.isoformat(),
                    'last_report_date': last_report.shift_date.isoformat(),
                    'total_period_days': (last_report.shift_date - first_report.shift_date).days + 1,
                    'active_days': len(set(r.shift_date for r in reports)),
                    'activity_ratio': len(set(r.shift_date for r in reports)) / ((last_report.shift_date - first_report.shift_date).days + 1)
                }
            print("[OK] Временная статистика рассчитана")
        except Exception as e:
            print(f"[ERROR] Ошибка при расчете временной статистики: {str(e)}")
            import traceback
            traceback.print_exc()
            time_stats = {}
        
        print("[WORK] Начинаем расчет статистики по типам смен...")
        # Статистика по типам смен
        try:
            shift_stats = {
                'morning_shifts': len([r for r in reports if r.shift_type == 'morning']),
                'evening_shifts': len([r for r in reports if r.shift_type == 'evening']),
                'morning_profit': sum(calculate_profit_from_orders(db.session, r)['salary_profit'] for r in reports if r.shift_type == 'morning'),
                'evening_profit': sum(calculate_profit_from_orders(db.session, r)['salary_profit'] for r in reports if r.shift_type == 'evening')
            }
            print("[OK] Статистика по типам смен рассчитана")
        except Exception as e:
            print(f"[ERROR] Ошибка при расчете статистики по типам смен: {str(e)}")
            import traceback
            traceback.print_exc()
            shift_stats = {
                'morning_shifts': 0,
                'evening_shifts': 0,
                'morning_profit': 0,
                'evening_profit': 0
            }
        
        print("[WORK] Начинаем расчет средних показателей...")
        # Средние показатели
        avg_stats = {}
        try:
            if reports:
                avg_stats = {
                    'avg_requests_per_shift': sum(r.total_requests or 0 for r in reports) / len(reports),
                    'avg_profit_per_shift': total_salary_profit / len(reports),
                    'avg_project_profit_per_shift': total_project_profit / len(reports),
                    'avg_bybit_per_shift': sum(r.bybit_requests or 0 for r in reports) / len(reports),
                    'avg_htx_per_shift': sum(r.htx_requests or 0 for r in reports) / len(reports),
                    'avg_bliss_per_shift': sum(r.bliss_requests or 0 for r in reports) / len(reports)
                }
            print("[OK] Средние показатели рассчитаны")
        except Exception as e:
            print(f"[ERROR] Ошибка при расчете средних показателей: {str(e)}")
            import traceback
            traceback.print_exc()
            avg_stats = {}
        
        print("[WORK] Начинаем расчет лучших и худших показателей...")
        # Лучшие и худшие показатели
        best_worst = {}
        try:
            if reports:
                profits = [calculate_profit_from_orders(db.session, r)['salary_profit'] for r in reports]
                best_report = max(reports, key=lambda r: calculate_profit_from_orders(db.session, r)['salary_profit'])
                worst_report = min(reports, key=lambda r: calculate_profit_from_orders(db.session, r)['salary_profit'])
                
                best_worst = {
                    'best_profit': {
                        'amount': max(profits),
                        'date': best_report.shift_date.isoformat(),
                        'shift_type': best_report.shift_type
                    },
                    'worst_profit': {
                        'amount': min(profits),
                        'date': worst_report.shift_date.isoformat(),
                        'shift_type': worst_report.shift_type
                    },
                    'most_requests': {
                        'count': max(r.total_requests or 0 for r in reports),
                        'date': max(reports, key=lambda r: r.total_requests or 0).shift_date.isoformat()
                    }
                }
            print("[OK] Лучшие и худшие показатели рассчитаны")
        except Exception as e:
            print(f"[ERROR] Ошибка при расчете лучших и худших показателей: {str(e)}")
            import traceback
            traceback.print_exc()
            best_worst = {}
        
        print("[WORK] Формируем итоговый профиль...")
        # Формируем итоговый профиль
        try:
            profile = {
                'employee': {
                    'id': employee.id,
                    'name': employee.name,
                    'telegram': employee.telegram,
                    'salary_percent': employee.salary_percent or 30.0,
                    'is_active': employee.is_active,
                    'created_at': employee.created_at.isoformat() if employee.created_at else None
                },
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'basic_stats': basic_stats,
                'report_details': report_details,
                'order_stats': order_stats,
                'time_stats': time_stats,
                'shift_stats': shift_stats,
                'avg_stats': avg_stats,
                'best_worst': best_worst,
                'platform_profits': platform_profits
            }
            
            print("[OK] Итоговый профиль сформирован")
            print("[WORK] Отправляем ответ...")
            return jsonify(profile)
        except Exception as e:
            print(f"[ERROR] Ошибка при формировании итогового профиля: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def process_shift_files(report_id, employee_id, shift_start_time, shift_end_time, files_data, shift_start_date=None, shift_end_date=None):
    """
    Обрабатывает файлы выгрузок для смены с автоматической проверкой времени
    
    Args:
        report_id: ID отчёта
        employee_id: ID сотрудника
        shift_start_time: время начала смены по МСК
        shift_end_time: время окончания смены по МСК
        files_data: словарь с файлами {platform: file_path}
        shift_start_date: дата начала диапазона (опционально)
        shift_end_date: дата окончания диапазона (опционально)
    
    Returns:
        dict: статистика обработки файлов
    """
    from utils import link_orders_to_employee
    
    stats = {
        'total_orders': 0,
        'linked_orders': 0,
        'platforms_processed': [],
        'errors': []
    }
    
    try:
        # Получаем аккаунты сотрудника
        employee_accounts = Account.query.filter_by(
            employee_id=employee_id,
            is_active=True
        ).all()
        
        if not employee_accounts:
            stats['errors'].append('У сотрудника нет активных аккаунтов')
            return stats
        
        # Группируем аккаунты по платформам
        platform_accounts = {}
        for account in employee_accounts:
            if account.platform not in platform_accounts:
                platform_accounts[account.platform] = []
            platform_accounts[account.platform].append(account.id)
        
        # Обрабатываем каждый файл
        for platform, file_path in files_data.items():
            if not file_path or not os.path.exists(file_path):
                continue
                
            try:
                print(f"Обрабатываем файл {platform}: {file_path}")
                
                # Проверяем, есть ли у сотрудника аккаунты на этой платформе
                # Для bybit_btc используем те же аккаунты что и для bybit
                actual_platform = 'bybit' if platform == 'bybit_btc' else platform
                if actual_platform not in platform_accounts:
                    print(f"У сотрудника нет аккаунтов на платформе {actual_platform}")
                    continue
                
                # Обрабатываем файл для каждого аккаунта на этой платформе
                # Для bybit_btc используем аккаунты bybit
                target_platform = 'bybit' if platform == 'bybit_btc' else platform
                for account_id in platform_accounts[target_platform]:
                    account_stats = process_platform_file(
                        file_path,
                        platform,  # Передаем оригинальную платформу (bybit_btc)
                        [account_id],  # Передаем только один аккаунт
                        shift_start_time,
                        shift_end_time,
                        report_id,
                        employee_id
                    )
                    
                    stats['total_orders'] += account_stats.get('total_orders', 0)
                    stats['linked_orders'] += account_stats.get('linked_orders', 0)
                
                if platform not in stats['platforms_processed']:
                    stats['platforms_processed'].append(platform)
                
                print(f"Обработано {stats['total_orders']} ордеров для {platform}, создано {stats['linked_orders']} новых")
                
            except Exception as e:
                error_msg = f"Ошибка обработки файла {platform}: {str(e)}"
                stats['errors'].append(error_msg)
                print(error_msg)
                continue
        
        return stats
        
    except Exception as e:
        stats['errors'].append(f"Общая ошибка обработки файлов: {str(e)}")
        return stats

@app.route('/api/employee-accounts/<int:employee_id>', methods=['GET'])
def get_employee_accounts(employee_id):
    """Возвращает все активные аккаунты, сгруппированные по площадкам"""
    try:
        # Получаем все активные аккаунты (не привязанные к конкретному сотруднику)
        accounts = Account.query.filter_by(is_active=True).all()
        
        # Группируем по площадкам
        accounts_by_platform = {}
        for account in accounts:
            platform = account.platform
            if platform not in accounts_by_platform:
                accounts_by_platform[platform] = []
            
            accounts_by_platform[platform].append({
                'id': account.id,
                'account_name': account.account_name,
                'platform': account.platform
            })
        
        return jsonify({
            'success': True,
            'accounts': accounts_by_platform
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def validate_shift_time_and_files(shift_start_time, shift_end_time, files_data, employee_accounts):
    """
    Валидирует время смены и проверяет соответствие файлов выгрузок аккаунтам сотрудника
    
    Args:
        shift_start_time: время начала смены по МСК
        shift_end_time: время окончания смены по МСК
        files_data: словарь с файлами {platform: file_path}
        employee_accounts: список аккаунтов сотрудника
    
    Returns:
        dict: результат валидации
    """
    validation_result = {
        'is_valid': True,
        'errors': [],
        'warnings': [],
        'file_validation': {}
    }
    
    # Проверяем время смены
    if not shift_start_time or not shift_end_time:
        validation_result['is_valid'] = False
        validation_result['errors'].append('Необходимо указать время начала и окончания смены')
        return validation_result
    
    if shift_start_time >= shift_end_time:
        validation_result['is_valid'] = False
        validation_result['errors'].append('Время начала смены должно быть раньше времени окончания')
        return validation_result
    
    # Проверяем длительность смены (не более 24 часов)
    shift_duration = shift_end_time - shift_start_time
    if shift_duration.total_seconds() > 24 * 3600:
        validation_result['warnings'].append('Длительность смены превышает 24 часа')
    
    # Получаем аккаунты сотрудника по площадкам
    employee_platforms = set(acc.platform for acc in employee_accounts)
    
    # Проверяем соответствие файлов выгрузок аккаунтам сотрудника
    for platform, file_path in files_data.items():
        if not file_path or not os.path.exists(file_path):
            continue
            
        if platform not in employee_platforms:
            validation_result['warnings'].append(
                f'Файл выгрузки {platform} загружен, но у сотрудника нет аккаунтов на этой площадке'
            )
        
        # Проверяем содержимое файла
        try:
            orders_data = parse_orders_file(
                file_path, 
                platform, 
                shift_start_time, 
                shift_end_time,
                os.path.basename(file_path)
            )
            
            # Проверяем, есть ли ордера в файле для аккаунтов сотрудника
            employee_account_names = [acc.account_name for acc in employee_accounts if acc.platform == platform]
            relevant_orders = [
                order for order in orders_data 
                if order.get('account_name') in employee_account_names
            ]
            
            validation_result['file_validation'][platform] = {
                'total_orders': len(orders_data),
                'employee_orders': len(relevant_orders),
                'account_names': employee_account_names,
                'has_orders_in_shift': len(relevant_orders) > 0
            }
            
            if len(relevant_orders) == 0:
                validation_result['warnings'].append(
                    f'В файле {platform} не найдено ордеров для аккаунтов сотрудника в указанное время смены'
                )
                
        except Exception as e:
            validation_result['errors'].append(f'Ошибка обработки файла {platform}: {str(e)}')
    
    return validation_result

@app.route('/api/validate-shift', methods=['POST'])
def validate_shift():
    """Валидирует время смены и файлы выгрузок"""
    try:
        if request.content_type and request.content_type.startswith('multipart/form-data'):
            form = request.form
            files = request.files
            
            # Получаем данные формы
            employee_id = form.get('employee_id')
            shift_start_time_str = form.get('shift_start_time')
            shift_end_time_str = form.get('shift_end_time')
            
            if not employee_id or not shift_start_time_str or not shift_end_time_str:
                return jsonify({'error': 'Необходимо указать сотрудника и время смены'}), 400
            
            # Парсим время
            try:
                shift_start_time = datetime.strptime(shift_start_time_str, '%Y-%m-%dT%H:%M')
                shift_end_time = datetime.strptime(shift_end_time_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                return jsonify({'error': 'Неверный формат времени'}), 400
            
            # Получаем аккаунты сотрудника
            employee_accounts = Account.query.filter_by(
                employee_id=employee_id,
                is_active=True
            ).all()
            
            if not employee_accounts:
                return jsonify({'error': 'У сотрудника нет активных аккаунтов'}), 400
            
            # Собираем файлы
            files_data = {}
            file_keys = ['bybit_file', 'bybit_btc_file', 'htx_file', 'bliss_file']
            
            for key in file_keys:
                if key in files and files[key].filename:
                    file = files[key]
                    if file and allowed_file(file.filename):
                        if not validate_file_size(file):
                            return jsonify({'error': f'Файл {file.filename} слишком большой (максимум 16MB)'}), 400
                        
                        # Сохраняем временный файл для валидации
                        filename = secure_filename(file.filename)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"temp_{timestamp}_{filename}"
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file.save(file_path)
                        
                        platform = key.replace('_file', '')
                        files_data[platform] = file_path
            
            # Валидируем
            validation_result = validate_shift_time_and_files(
                shift_start_time, 
                shift_end_time, 
                files_data, 
                employee_accounts
            )
            
            # Удаляем временные файлы
            for file_path in files_data.values():
                if os.path.exists(file_path):
                    os.remove(file_path)
            
            return jsonify(validation_result)
            
        else:
            return jsonify({'error': 'Неподдерживаемый тип контента'}), 400
            
    except Exception as e:
        return jsonify({'error': f'Ошибка валидации: {str(e)}'}), 500

@app.route('/api/reports/create-shift', methods=['POST'])
def create_shift_report():
    """Создает отчёт по смене с автоматической обработкой файлов выгрузок"""
    try:
        # Получаем данные из формы
        employee_id = request.form.get('employee_id')
        shift_date = request.form.get('shift_date')
        shift_start_time = request.form.get('shift_start_time')
        shift_end_time = request.form.get('shift_end_time')
        selected_accounts_json = request.form.get('selected_accounts', '{}')
        balances_json = request.form.get('balances', '{}')
        
        # Валидация обязательных полей
        if not all([employee_id, shift_date, shift_start_time, shift_end_time]):
            return jsonify({'error': 'Заполните все обязательные поля'}), 400
        
        # Определяем дату смены
        start_date = datetime.strptime(shift_date, '%Y-%m-%d').date()
        end_date = start_date
        
        # Парсим выбранные аккаунты и балансы
        try:
            selected_accounts = json.loads(selected_accounts_json)
            balances = json.loads(balances_json)
        except json.JSONDecodeError:
            return jsonify({'error': 'Неверный формат данных аккаунтов или балансов'}), 400
        
        # Преобразуем время в datetime объекты
        try:
            shift_start_dt = datetime.strptime(shift_start_time, '%Y-%m-%dT%H:%M')
            shift_end_dt = datetime.strptime(shift_end_time, '%Y-%m-%dT%H:%M')
            print(f"DEBUG SHIFT: Время смены (МСК): {shift_start_dt} - {shift_end_dt}")
        except ValueError:
            return jsonify({'error': 'Неверный формат времени'}), 400
        
        # Проверяем, что время начала меньше времени окончания
        if shift_start_dt >= shift_end_dt:
            return jsonify({'error': 'Время начала смены должно быть меньше времени окончания'}), 400
        
        # Определяем тип смены на основе времени начала
        shift_type = 'morning' if shift_start_dt.hour < 16 else 'evening'
        
        # Создаем отчет
        report = ShiftReport(
            employee_id=int(employee_id),
            shift_date=start_date,
            shift_type=shift_type,
            department=request.form.get('department', 'first'),
            shift_start_date=start_date,
            shift_end_date=end_date,
            shift_start_time=shift_start_dt,
            shift_end_time=shift_end_dt,
            balances_json=balances_json,  # Сохраняем балансы
            scam_amount=safe_float(request.form.get('scam_amount', 0)),
            scam_amount_rub=safe_float(request.form.get('scam_amount_rub', 0)),
            scam_platform=request.form.get('scam_platform', 'bybit'),
            scam_account=request.form.get('scam_account', ''),
            scam_comment=request.form.get('scam_comment', ''),

            scam_count_in_sales=parse_bool(request.form.get('scam_count_in_sales', False)),
            scam_count_in_purchases=parse_bool(request.form.get('scam_count_in_purchases', False)),
            dokidka_amount=safe_float(request.form.get('dokidka_amount', 0)),
            dokidka_amount_rub=safe_float(request.form.get('dokidka_amount_rub', 0)),
            dokidka_platform=request.form.get('dokidka_platform', 'bybit'),
            dokidka_account=request.form.get('dokidka_account', ''),
            dokidka_comment=request.form.get('dokidka_comment', ''),
            dokidka_count_in_sales=parse_bool(request.form.get('dokidka_count_in_sales', False)),
            dokidka_count_in_purchases=parse_bool(request.form.get('dokidka_count_in_purchases', False)),
            internal_transfer_amount=safe_float(request.form.get('internal_transfer_amount', 0)),
            internal_transfer_amount_rub=safe_float(request.form.get('internal_transfer_amount_rub', 0)),
            internal_transfer_platform=request.form.get('internal_transfer_platform', 'bybit'),
            internal_transfer_account=request.form.get('internal_transfer_account', ''),
            internal_transfer_comment=request.form.get('internal_transfer_comment', ''),
            internal_transfer_count_in_sales=parse_bool(request.form.get('internal_transfer_count_in_sales', False)),
            internal_transfer_count_in_purchases=parse_bool(request.form.get('internal_transfer_count_in_purchases', False)),
            appeal_amount=safe_float(request.form.get('appeal_amount', 0)),
            appeal_amount_rub=safe_float(request.form.get('appeal_amount_rub', 0)),
            appeal_platform=request.form.get('appeal_platform', 'bybit'),
            appeal_account=request.form.get('appeal_account', ''),
            appeal_comment=request.form.get('appeal_comment', ''),
            appeal_deducted=parse_bool(request.form.get('appeal_deducted', False)),
            appeal_count_in_sales=parse_bool(request.form.get('appeal_count_in_sales', False)),
            appeal_count_in_purchases=parse_bool(request.form.get('appeal_count_in_purchases', False))
        )
        
        # Отладочная информация для чекбоксов аппеляций
        print(f"[REPORT] appeal_count_in_sales = {request.form.get('appeal_count_in_sales')} -> {report.appeal_count_in_sales}")
        print(f"[REPORT] appeal_count_in_purchases = {request.form.get('appeal_count_in_purchases')} -> {report.appeal_count_in_purchases}")
        
        # Сохраняем фотографии
        # Проверяем существование директории uploads
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
            
        if 'start_photo' in request.files:
            file = request.files['start_photo']
            if file.filename:
                if not allowed_file(file.filename):
                    return jsonify({'error': f'Недопустимый тип файла для фото начала смены: {file.filename}. Разрешены только: png, jpg, jpeg, webp'}), 400
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                report.start_photo = filename
                
        if 'end_photo' in request.files:
            file = request.files['end_photo']
            if file.filename:
                if not allowed_file(file.filename):
                    return jsonify({'error': f'Недопустимый тип файла для фото конца смены: {file.filename}. Разрешены только: png, jpg, jpeg, webp'}), 400
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                report.end_photo = filename
        
        # Сохраняем отчет в базу
        db.session.add(report)
        db.session.commit()
        
        # Если скам отмечен как личный, сохраняем его в историю
        if report.scam_amount:
            scam_history = EmployeeScamHistory(
                employee_id=int(employee_id),
                shift_report_id=report.id,
                amount=report.scam_amount,
                date=report.shift_date,
                comment=report.scam_comment
            )
            db.session.add(scam_history)
            db.session.commit()
        
        # Если указана апелляция, создаем ордер в истории ордеров
        if report.appeal_amount and report.appeal_amount > 0:
            # Получаем информацию о сотруднике для определения аккаунта
            employee = Employee.query.get(int(employee_id))
            if employee:
                # Получаем данные апелляции из формы
                appeal_amount_usdt = float(report.appeal_amount)
                appeal_amount_rub = safe_float(request.form.get('appeal_amount_rub', 0))
                appeal_platform = request.form.get('appeal_platform', 'bybit')
                appeal_account = request.form.get('appeal_account', f"{employee.name}_appeal")
                
                # Рассчитываем курс
                if appeal_amount_rub > 0 and appeal_amount_usdt > 0:
                    price = appeal_amount_rub / appeal_amount_usdt
                else:
                    # Используем средний курс за день или 1.0
                    price = 1.0
                
                # Создаем ордер апелляции
                appeal_order = Order(
                    order_id=f"appeal_{report.id}_{int(datetime.utcnow().timestamp())}",
                    employee_id=int(employee_id),
                    platform=appeal_platform,
                    account_name=appeal_account,
                    symbol='USDT',
                    side='sell',  # Апелляция обычно как продажа
                    quantity=appeal_amount_usdt,
                    price=price,
                    total_usdt=appeal_amount_rub if appeal_amount_rub > 0 else appeal_amount_usdt,
                    fees_usdt=0,
                    status='appealed',  # Специальный статус для апелляций
                    count_in_sales=report.appeal_count_in_sales,  # Учитываем в продажах если установлен чекбокс
                    count_in_purchases=report.appeal_count_in_purchases,  # Учитываем в покупках если установлен чекбокс
                    executed_at=shift_start_dt  # Используем время начала смены
                )
                
                db.session.add(appeal_order)
                db.session.commit()
                
                print(f"Создан ордер апелляции: {appeal_order.order_id}, сумма: {appeal_amount_usdt} USDT, {appeal_amount_rub} RUB, платформа: {appeal_platform}, аккаунт: {appeal_account}")
                print(f"[APPEAL ORDER] count_in_sales = {appeal_order.count_in_sales}, count_in_purchases = {appeal_order.count_in_purchases}")
        
        # Если указана докидка, создаем ордер в истории ордеров
        if report.dokidka_amount and report.dokidka_amount > 0:
            # Получаем информацию о сотруднике для определения аккаунта
            employee = Employee.query.get(int(employee_id))
            if employee:
                # Получаем данные докидки из формы
                dokidka_amount_usdt = float(report.dokidka_amount)
                dokidka_amount_rub = float(report.dokidka_amount_rub) if report.dokidka_amount_rub else 0
                dokidka_platform = report.dokidka_platform or 'bybit'
                dokidka_account = report.dokidka_account or f"{employee.name}_dokidka"
                
                # Рассчитываем курс
                if dokidka_amount_rub > 0 and dokidka_amount_usdt > 0:
                    price = dokidka_amount_rub / dokidka_amount_usdt
                else:
                    # Используем средний курс за день или 1.0
                    price = 1.0
                
                # Создаем ордер докидки
                dokidka_order = Order(
                    order_id=f"dokidka_{report.id}_{int(datetime.utcnow().timestamp())}",
                    employee_id=int(employee_id),
                    platform=dokidka_platform,
                    account_name=dokidka_account,
                    symbol='USDT',
                    side='sell',  # Докидка обычно как продажа
                    quantity=dokidka_amount_usdt,
                    price=price,
                    total_usdt=dokidka_amount_rub if dokidka_amount_rub > 0 else dokidka_amount_usdt,
                    fees_usdt=0,
                    status='dokidka',  # Специальный статус для докидок
                    count_in_sales=report.dokidka_count_in_sales,  # Учитываем в продажах если установлен чекбокс
                    count_in_purchases=report.dokidka_count_in_purchases,  # Учитываем в покупках если установлен чекбокс
                    executed_at=shift_start_dt  # Используем время начала смены
                )
                
                db.session.add(dokidka_order)
                db.session.commit()
                
                print(f"Создан ордер докидки: {dokidka_order.order_id}, сумма: {dokidka_amount_usdt} USDT, {dokidka_amount_rub} RUB, платформа: {dokidka_platform}, аккаунт: {dokidka_account}")
        
        # Если указан скам, создаем ордер в истории ордеров
        if report.scam_amount and report.scam_amount > 0:
            # Получаем информацию о сотруднике для определения аккаунта
            employee = Employee.query.get(int(employee_id))
            if employee:
                # Получаем данные скама из формы
                scam_amount_usdt = float(report.scam_amount)
                scam_amount_rub = float(report.scam_amount_rub) if report.scam_amount_rub else 0
                scam_platform = report.scam_platform or 'bybit'
                scam_account = report.scam_account or f"{employee.name}_scam"
                
                # Рассчитываем курс
                if scam_amount_rub > 0 and scam_amount_usdt > 0:
                    price = scam_amount_rub / scam_amount_usdt
                else:
                    # Используем средний курс за день или 1.0
                    price = 1.0
                
                # Создаем ордер скама
                scam_order = Order(
                    order_id=f"scam_{report.id}_{int(datetime.utcnow().timestamp())}",
                    employee_id=int(employee_id),
                    platform=scam_platform,
                    account_name=scam_account,
                    symbol='USDT',
                    side='sell',  # Скам обычно как продажа
                    quantity=scam_amount_usdt,
                    price=price,
                    total_usdt=scam_amount_rub if scam_amount_rub > 0 else scam_amount_usdt,
                    fees_usdt=0,
                    status='scam',  # Специальный статус для скамов
                    count_in_sales=report.scam_count_in_sales,  # Учитываем в продажах если установлен чекбокс
                    count_in_purchases=report.scam_count_in_purchases,  # Учитываем в покупках если установлен чекбокс
                    executed_at=shift_start_dt  # Используем время начала смены
                )
                
                db.session.add(scam_order)
                db.session.commit()
                
                print(f"Создан ордер скама: {scam_order.order_id}, сумма: {scam_amount_usdt} USDT, {scam_amount_rub} RUB, платформа: {scam_platform}, аккаунт: {scam_account}")
        
        # Если указан внутренний перевод, создаем ордер в истории ордеров
        if report.internal_transfer_amount and report.internal_transfer_amount > 0:
            # Получаем информацию о сотруднике для определения аккаунта
            employee = Employee.query.get(int(employee_id))
            if employee:
                # Получаем данные внутреннего перевода из формы
                internal_transfer_amount_usdt = float(report.internal_transfer_amount)
                internal_transfer_amount_rub = float(report.internal_transfer_amount_rub) if report.internal_transfer_amount_rub else 0
                internal_transfer_platform = report.internal_transfer_platform or 'bybit'
                internal_transfer_account = report.internal_transfer_account or f"{employee.name}_internal"
                
                # Рассчитываем курс
                if internal_transfer_amount_rub > 0 and internal_transfer_amount_usdt > 0:
                    price = internal_transfer_amount_rub / internal_transfer_amount_usdt
                else:
                    # Используем средний курс за день или 1.0
                    price = 1.0
                
                # Создаем ордер внутреннего перевода
                internal_transfer_order = Order(
                    order_id=f"internal_transfer_{report.id}_{int(datetime.utcnow().timestamp())}",
                    employee_id=int(employee_id),
                    platform=internal_transfer_platform,
                    account_name=internal_transfer_account,
                    symbol='USDT',
                    side='sell',  # Внутренний перевод обычно как продажа
                    quantity=internal_transfer_amount_usdt,
                    price=price,
                    total_usdt=internal_transfer_amount_rub if internal_transfer_amount_rub > 0 else internal_transfer_amount_usdt,
                    fees_usdt=0,
                    status='internal_transfer',  # Специальный статус для внутренних переводов
                    count_in_sales=report.internal_transfer_count_in_sales,  # Учитываем в продажах если установлен чекбокс
                    count_in_purchases=report.internal_transfer_count_in_purchases,  # Учитываем в покупках если установлен чекбокс
                    executed_at=shift_start_dt  # Используем время начала смены
                )
                
                db.session.add(internal_transfer_order)
                db.session.commit()
                
                print(f"Создан ордер внутреннего перевода: {internal_transfer_order.order_id}, сумма: {internal_transfer_amount_usdt} USDT, {internal_transfer_amount_rub} RUB, платформа: {internal_transfer_platform}, аккаунт: {internal_transfer_account}")
        
        # Обрабатываем файлы выгрузок и привязываем ордера
        stats = {
            'total_orders': 0,
            'linked_orders': 0,
            'platforms_processed': [],
            'errors': []
        }
        
        # Обрабатываем файлы для каждого аккаунта
        for platform in ['bybit', 'htx', 'bliss', 'gate']:
            if platform in selected_accounts and selected_accounts[platform]:
                platform_stats = {
                    'total_orders': 0,
                    'linked_orders': 0,
                    'errors': []
                }
                
                for account_id in selected_accounts[platform]:
                    if platform == 'gate':
                        # Для Gate обрабатываем суммы вместо файлов
                        gate_amount_key = f'gate_amount_{account_id}'
                        gate_amount_rub_key = f'gate_amount_rub_{account_id}'
                        
                        if gate_amount_key in request.form:
                            try:
                                gate_amount = float(request.form[gate_amount_key])
                                gate_amount_rub = float(request.form.get(gate_amount_rub_key, 0))
                                print(f"Обрабатываем сумму Gate для аккаунта {account_id}: {gate_amount} USDT, {gate_amount_rub} RUB")
                                print(f"DEBUG: Все данные формы для Gate: {dict(request.form)}")
                                
                                # Создаем фиктивный ордер для Gate с указанной суммой
                                # GATE всегда идет как покупка
                                # Если указана сумма в рублях, используем её как price, иначе 1.0
                                price = gate_amount_rub / gate_amount if gate_amount > 0 and gate_amount_rub > 0 else 1.0
                                
                                gate_order = Order(
                                    order_id=f'gate_manual_{report.id}_{account_id}_{int(datetime.utcnow().timestamp())}',
                                    employee_id=int(employee_id),
                                    platform='gate',
                                    account_name=next((acc.account_name for acc in Account.query.filter_by(id=account_id).all()), 'Unknown'),
                                    symbol='USDT',
                                    side='buy',  # GATE всегда идет как покупка
                                    quantity=gate_amount,
                                    price=price,  # Курс RUB/USDT или 1.0
                                    total_usdt=gate_amount_rub,  # Используем сумму в рублях
                                    fees_usdt=0,
                                    status='filled',
                                    executed_at=shift_start_dt  # Используем время начала смены
                                )
                                
                                db.session.add(gate_order)
                                platform_stats['linked_orders'] += 1
                                
                                # Сохраняем изменения в базе данных
                                db.session.commit()
                                
                            except Exception as e:
                                error_msg = f'Ошибка обработки суммы Gate для аккаунта {account_id}: {str(e)}'
                                platform_stats['errors'].append(error_msg)
                                print(error_msg)
                    else:
                        # Для остальных площадок обрабатываем файлы
                        file_key = f'file_{platform}_{account_id}'
                        if file_key in request.files:
                            file = request.files[file_key]
                            if file.filename:
                                try:
                                    # Сохраняем файл и получаем путь
                                    file_path = save_report_file(file, platform, report.id)
                                    if not file_path:
                                        continue
                                    
                                    print(f"Обрабатываем файл {platform} для аккаунта {account_id}: {file_path}")
                                    
                                    # Обрабатываем файл и привязываем ордера для конкретного аккаунта
                                    account_stats = process_platform_file(
                                        file_path, 
                                        platform, 
                                        [account_id],  # Передаем только один аккаунт
                                        shift_start_dt, 
                                        shift_end_dt,
                                        report.id,
                                        int(employee_id)
                                    )
                                    
                                    platform_stats['total_orders'] += account_stats.get('total_orders', 0)
                                    platform_stats['linked_orders'] += account_stats.get('linked_orders', 0)
                                    
                                    if account_stats.get('errors'):
                                        platform_stats['errors'].extend(account_stats['errors'])
                                    
                                except Exception as e:
                                    error_msg = f'Ошибка обработки файла {platform} для аккаунта {account_id}: {str(e)}'
                                    platform_stats['errors'].append(error_msg)
                                    print(error_msg)
                        
                        # Обрабатываем BTC файлы для Bybit (если есть)
                        if platform == 'bybit':
                            btc_file_key = f'file_bybit_btc_{account_id}'
                            if btc_file_key in request.files:
                                btc_file = request.files[btc_file_key]
                                if btc_file.filename:
                                    try:
                                        # Сохраняем BTC файл и получаем путь
                                        btc_file_path = save_report_file(btc_file, 'bybit_btc', report.id)
                                        if btc_file_path:
                                            print(f"Обрабатываем BTC файл для аккаунта {account_id}: {btc_file_path}")
                                            
                                            # Обрабатываем BTC файл и привязываем ордера
                                            btc_account_stats = process_platform_file(
                                                btc_file_path, 
                                                'bybit_btc', 
                                                [account_id],  # Передаем только один аккаунт
                                                shift_start_dt, 
                                                shift_end_dt,
                                                report.id,
                                                int(employee_id)
                                            )
                                            
                                            platform_stats['total_orders'] += btc_account_stats.get('total_orders', 0)
                                            platform_stats['linked_orders'] += btc_account_stats.get('linked_orders', 0)
                                            
                                            if btc_account_stats.get('errors'):
                                                platform_stats['errors'].extend(btc_account_stats['errors'])
                                        
                                    except Exception as e:
                                        error_msg = f'Ошибка обработки BTC файла для аккаунта {account_id}: {str(e)}'
                                        platform_stats['errors'].append(error_msg)
                                        print(error_msg)
                
                # Обновляем общую статистику
                stats['total_orders'] += platform_stats['total_orders']
                stats['linked_orders'] += platform_stats['linked_orders']
                
                if platform_stats['total_orders'] > 0 or platform_stats['linked_orders'] > 0:
                    stats['platforms_processed'].append(platform.upper())
                
                if platform_stats['errors']:
                    stats['errors'].extend(platform_stats['errors'])
        
        return jsonify({
            'id': report.id,
            'message': 'Report created successfully',
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({'error': f'Ошибка создания отчёта: {str(e)}'}), 500


def process_platform_file(file_path, platform, account_ids, shift_start_dt, shift_end_dt, report_id, employee_id):
    """Обрабатывает файл выгрузки для конкретной площадки с поддержкой диапазона дат и времени внутри дня"""
    print(f"\nDEBUG SHIFT: Обработка файла {platform}")
    print(f"DEBUG SHIFT: Время смены {shift_start_dt} - {shift_end_dt}")
    
    stats = {
        'total_orders': 0,
        'linked_orders': 0,
        'errors': []
    }
    
    try:
        from datetime import timedelta, time
        # Получаем аккаунты для проверки
        accounts = Account.query.filter(Account.id.in_(account_ids)).all()
        account_names = [acc.account_name for acc in accounts]
        
        if not account_names:
            stats['errors'].append(f'Не найдены аккаунты с ID: {account_ids}')
            return stats
        
        # Читаем файл в зависимости от платформы
        orders = parse_orders_file(file_path, platform)
        if not orders:
            stats['errors'].append(f'Не удалось прочитать файл для платформы: {platform}')
            return stats
        
        # Для bybit_btc сохраняем платформу как 'bybit_btc' в БД для правильной фильтрации
        db_platform = platform  # Сохраняем оригинальную платформу
        
        stats['total_orders'] = len(orders)
        
        # Если в выгрузке отсутствует поле account_name, привяжем все ордера к текущему аккаунту
        # (передаём всегда только один account_id на вызов)
        if len(account_names) == 1:
            default_account_name = account_names[0]
        else:
            default_account_name = None
        
        # Приводим имена аккаунтов к нижнему регистру для сравнения
        account_names_lower = [name.lower() for name in account_names]
        
        # Фильтруем ордера по времени смены
        account_orders = []
        for order in orders:
            order_time = order['executed_at']
            if shift_start_dt <= order_time <= shift_end_dt:
                account_orders.append(order)
        
        # Сохраняем отфильтрованные ордера
        created_count = 0
        for order in account_orders:
            try:
                # Проверяем, что ордер еще не существует
                existing_order = Order.query.filter_by(
                    order_id=order['order_id'],
                    platform=platform
                ).first()
                
                if existing_order:
                    print(f"Ордер уже существует: {order['order_id']}")
                    continue
                
                # Дополнительная проверка для BTC ордеров по содержимому
                if platform == 'bybit_btc':
                    # Проверяем существование ордера с теми же ключевыми полями
                    duplicate_order = Order.query.filter_by(
                        platform='bybit_btc',
                        symbol=order['symbol'],
                        side=order['side'],
                        quantity=order['quantity'],
                        price=order['price'],
                        executed_at=order['executed_at']
                    ).first()
                    
                    if duplicate_order:
                        print(f"BTC ордер с такими же данными уже существует: {duplicate_order.order_id}")
                        continue
                
                # Создаем новый ордер
                new_order = Order(
                    order_id=order['order_id'],
                    employee_id=employee_id,
                    platform=db_platform,  # Используем db_platform для правильного сохранения
                    account_name=default_account_name,  # Всегда используем имя выбранного аккаунта
                    symbol=order['symbol'],
                    side=order['side'],
                    quantity=order['quantity'],
                    price=order['price'],
                    total_usdt=order['total_usdt'],
                    fees_usdt=order.get('fees_usdt', 0),
                    status=order.get('status', 'filled'),
                    executed_at=order['executed_at']
                )
                
                db.session.add(new_order)
                created_count += 1
                print(f"Создан новый ордер: {order['order_id']} для аккаунта {order.get('account_name')}")
                
            except Exception as e:
                print(f"Ошибка сохранения ордера {order.get('order_id')}: {str(e)}")
                continue
        
        # Сохраняем изменения
        db.session.commit()
        
        stats['linked_orders'] = created_count
        print(f"Обработано {len(account_orders)} ордеров для {platform}, создано {created_count} новых")
        
        return stats
        
    except Exception as e:
        stats['errors'].append(str(e))
        return stats

@app.route('/api/employee-scams/<int:employee_id>', methods=['GET'])
def get_employee_scams(employee_id):
    """Получает историю скамов сотрудника"""
    try:
        # Проверяем существование сотрудника
        employee = Employee.query.get(employee_id)
        if not employee:
            return jsonify({'error': 'Сотрудник не найден'}), 404
            
        # Получаем все скамы сотрудника, сортируем по дате (сначала новые)
        scams = EmployeeScamHistory.query.filter_by(employee_id=employee_id).order_by(EmployeeScamHistory.date.desc()).all()
        
        # Форматируем данные для ответа
        scams_data = []
        total_amount = 0
        
        for scam in scams:
            scam_data = {
                'id': scam.id,
                'date': scam.date.strftime('%Y-%m-%d'),
                'amount': float(scam.amount),
                'comment': scam.comment,
                'shift_report_id': scam.shift_report_id
            }
            scams_data.append(scam_data)
            total_amount += float(scam.amount)
        
        return jsonify({
            'employee_id': employee_id,
            'employee_name': employee.name,
            'scams': scams_data,
            'total_amount': total_amount
        })
        
    except Exception as e:
        return jsonify({'error': f'Ошибка получения истории скамов: {str(e)}'}), 500

@app.route('/api/settings/salary', methods=['GET'])
def get_salary_settings():
    """Получает настройки расчета зарплаты"""
    try:
        settings = SalarySettings.query.first()
        if not settings:
            settings = SalarySettings()
            db.session.add(settings)
            db.session.commit()
            
        return jsonify({
            'base_percent': settings.base_percent,
            'min_daily_profit': settings.min_daily_profit,
            'bonus_percent': settings.bonus_percent,
            'bonus_profit_threshold': settings.bonus_profit_threshold
        })
    except Exception as e:
        print('Error getting salary settings:', e)
        return jsonify({'error': 'Ошибка при получении настроек'}), 500

@app.route('/api/settings/salary', methods=['POST'])
def update_salary_settings():
    """Обновляет настройки расчета зарплаты"""
    try:
        data = request.get_json()
        
        # Проверяем пароль администратора
        if not validate_admin_password({'password': data.get('password')}):
            return jsonify({'error': 'Неверный пароль администратора'}), 403
        
        settings = SalarySettings.query.first()
        if not settings:
            settings = SalarySettings()
            db.session.add(settings)
        
        # Обновляем настройки
        settings.base_percent = data.get('base_percent', settings.base_percent)
        settings.min_daily_profit = data.get('min_daily_profit', settings.min_daily_profit)
        settings.bonus_percent = data.get('bonus_percent', settings.bonus_percent)
        settings.bonus_profit_threshold = data.get('bonus_profit_threshold', settings.bonus_profit_threshold)
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        print('Error updating salary settings:', e)
        return jsonify({'error': 'Ошибка при обновлении настроек'}), 500

@app.route('/api/employee-salary/<int:employee_id>', methods=['GET'])
def get_employee_salary(employee_id):
    """Получает расчет зарплаты сотрудника на основе средней ежедневной прибыли"""
    try:
        from utils import calculate_salary_based_on_daily_profit
        
        # Получаем параметры периода
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date or not end_date:
            return jsonify({'error': 'Необходимо указать start_date и end_date'}), 400
        
        # Рассчитываем зарплату
        salary_data = calculate_salary_based_on_daily_profit(employee_id, start_date, end_date, db.session)
        
        if 'error' in salary_data:
            return jsonify({'error': salary_data['error']}), 400
        
        return jsonify(salary_data)
        
    except Exception as e:
        return jsonify({'error': f'Ошибка расчета зарплаты: {str(e)}'}), 500

def calculate_employee_statistics(reports, emp, db):
    """Вычисляет подробную статистику по одному сотруднику для /api/statistics (смены, заявки, прибыль, скам, переводы, зарплата и т.д.)."""
    if not reports:
        return {
            'id': emp.id,
            'name': emp.name,
            'telegram': emp.telegram,
            'total_days': 0,
            'total_shifts': 0,
            'total_requests': 0,
            'avg_requests_per_day': 0,
            'total_profit': 0,
            'net_profit': 0,
            'salary': 0,
            'total_scam': 0,
            'total_transfer': 0,
            'avg_profit_per_shift': 0,
            'total_bybit': 0,
            'total_htx': 0,
            'total_bliss': 0
        }
    # Используем total_requests если есть, иначе сумму по платформам
    total_requests_from_platforms = sum((r.bybit_requests or 0) + (r.htx_requests or 0) + (r.bliss_requests or 0) for r in reports)
    total_requests_from_field = sum(r.total_requests or 0 for r in reports)
    total_requests = max(total_requests_from_platforms, total_requests_from_field)
    
    total_bybit = sum(r.bybit_requests or 0 for r in reports)
    total_htx = sum(r.htx_requests or 0 for r in reports)
    total_bliss = sum(r.bliss_requests or 0 for r in reports)
    # Считаем только скамы по вине сотрудника
    total_scam = float(sum(r.scam_amount or 0 for r in reports if getattr(r, 'scam_personal', False)))
    total_transfer = float(sum(r.dokidka_amount or 0 for r in reports))
    # Считаем прибыль по новой логике
    total_project_profit = sum(calculate_report_profit(db.session, r)['project_profit'] for r in reports)
    total_salary_profit = sum(calculate_report_profit(db.session, r)['salary_profit'] for r in reports)
    # Используем индивидуальный процент сотрудника, если задан, иначе 30%
    salary_percent = emp.salary_percent if emp.salary_percent is not None else 30.0
    salary = max(0, total_salary_profit * (salary_percent / 100))
    total_shifts = len(reports)
    total_days = len(set(r.shift_date for r in reports))
    avg_requests_per_day = total_requests / total_days if total_days else 0
    avg_profit_per_shift = total_salary_profit / total_shifts if total_shifts else 0
    return {
        'id': emp.id,
        'name': emp.name,
        'telegram': emp.telegram,
        'total_days': total_days,
        'total_shifts': total_shifts,
        'total_requests': total_requests,
        'total_bybit': total_bybit,
        'total_htx': total_htx,
        'total_bliss': total_bliss,
        'avg_requests_per_day': round(avg_requests_per_day,2),
        'total_profit': round(total_project_profit,2),
        'net_profit': round(total_salary_profit,2),
        'salary': round(salary,2),
        'total_scam': round(total_scam,2),
        'total_transfer': round(total_transfer,2),
        'avg_profit_per_shift': round(avg_profit_per_shift,2)
    }

@app.route('/api/statistics', methods=['GET'])
def statistics():
    """Возвращает подробную статистику по сотрудникам за выбранный период: смены, заявки, прибыль, скам, переводы, зарплата и т.д."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    if not start_date or not end_date:
        today = datetime.now().date()
        start_date = today.replace(day=1)
        end_date = today
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    employees = Employee.query.filter_by(is_active=True).all()
    stats = []
    for emp in employees:
        reports = ShiftReport.query.filter(
            ShiftReport.employee_id == emp.id,
            ShiftReport.shift_date >= start_date,
            ShiftReport.shift_date <= end_date
        ).all()
        stats.append(calculate_employee_statistics(reports, emp, db))
    return jsonify(stats)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000) 