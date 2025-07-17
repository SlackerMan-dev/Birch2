// Content script для отслеживания ордеров на Bybit
class BybitOrderTracker {
  constructor() {
    this.settings = {
      serverUrl: 'http://localhost:5000',
      employeeId: null,
      accountName: '',
      trackingEnabled: false
    };
    this.observer = null;
    this.processedOrders = new Set();
    this.init();
  }

  async init() {
    // Загружаем настройки
    await this.loadSettings();
    
    // Слушаем сообщения от popup
    chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
      if (message.action === 'updateSettings') {
        this.settings = message.settings;
        this.updateTracking();
      } else if (message.action === 'loadExistingOrders') {
        this.loadExistingOrders(message.settings).then(sendResponse);
        return true; // Асинхронный ответ
      }
    });

    // Начинаем отслеживание
    this.startTracking();
  }

  async loadSettings() {
    try {
      const result = await chrome.storage.sync.get([
        'serverUrl',
        'employeeId',
        'accountName',
        'trackingEnabled'
      ]);
      
      this.settings = {
        serverUrl: result.serverUrl || 'http://localhost:5000',
        employeeId: result.employeeId || null,
        accountName: result.accountName || '',
        trackingEnabled: result.trackingEnabled || false
      };
      
      console.log('⚙️ Настройки загружены:', this.settings);
      
      // Проверяем соединение с сервером
      await this.checkServerConnection();
      
    } catch (error) {
      console.error('Ошибка загрузки настроек:', error);
      this.settings = {
        serverUrl: 'http://localhost:5000',
        employeeId: null,
        accountName: '',
        trackingEnabled: false
      };
    }
  }

  async checkServerConnection() {
    try {
      console.log('🔍 Проверяем соединение с сервером:', this.settings.serverUrl);
      
      const response = await fetch(`${this.settings.serverUrl}/api/employees`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      if (response.ok) {
        console.log('✅ Соединение с сервером установлено');
        this.showSuccessNotification('Соединение с сервером установлено');
      } else {
        console.warn('⚠️ Сервер отвечает с ошибкой:', response.status);
        this.showErrorNotification(`Сервер отвечает с ошибкой: ${response.status}`);
      }
    } catch (error) {
      console.error('❌ Не удалось подключиться к серверу:', error);
      this.showErrorNotification('Не удалось подключиться к серверу. Проверьте настройки.');
    }
  }

  startTracking() {
    if (!this.settings.trackingEnabled || !this.settings.employeeId) {
      console.log('Отслеживание отключено или не настроен сотрудник');
      return;
    }

    // Ждем загрузки страницы
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.setupObserver());
    } else {
      this.setupObserver();
    }
  }

  setupObserver() {
    // Наблюдаем за изменениями в DOM
    this.observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.type === 'childList') {
          this.checkForNewOrders();
        }
      });
    });

    // Начинаем наблюдение
    this.observer.observe(document.body, {
      childList: true,
      subtree: true
    });

    // Первоначальная проверка
    this.checkForNewOrders();
  }

  checkForNewOrders() {
    // Ищем таблицы с ордерами
    const orderTables = document.querySelectorAll('[data-testid="order-table"], .order-table, table');
    
    orderTables.forEach(table => {
      const rows = table.querySelectorAll('tr');
      rows.forEach(row => {
        this.processOrderRow(row);
      });
    });

    // Ищем div-элементы с ордерами (для современных веб-приложений)
    this.checkForDivOrders();

    // Ищем уведомления о завершении ордеров
    this.checkOrderNotifications();
  }

    checkForDivOrders() {
    // Сначала ищем элементы с высокой вероятностью содержания ордеров
    const prioritySelectors = [
      'tbody tr',                 // Строки в tbody (самый вероятный)
      '.ant-table-tbody > tr',    // Прямые дочерние строки tbody
      'tr:not(:first-child)',     // Строки таблиц (кроме заголовков)
    ];

    let foundOrders = false;
    
    // Проверяем приоритетные селекторы
    for (const selector of prioritySelectors) {
      const elements = document.querySelectorAll(selector);
      console.log(`Проверяем селектор ${selector}: найдено ${elements.length} элементов`);
      
      elements.forEach(element => {
        const elementText = element.textContent;
        // Проверяем, что элемент содержит реальные данные ордера
        if (this.isLikelyOrderElement(elementText)) {
          console.log(`Найден потенциальный ордер в ${selector}:`, elementText.substring(0, 100));
          this.processOrderElement(element);
          foundOrders = true;
        }
      });
      
      // Если нашли ордера в приоритетных селекторах, не ищем в остальных
      if (foundOrders) {
        console.log(`Найдены ордера в приоритетном селекторе ${selector}, прекращаем поиск`);
        return;
      }
    }

    // Если не нашли в приоритетных, ищем в остальных
    const otherSelectors = [
      '.ant-table-row',           // Ant Design таблицы
      '[data-row-key]',           // Строки с data-row-key
      '.order-row',               // Строки ордеров
      '.trade-row',               // Строки сделок
      '.history-row',             // Строки истории
      '[class*="order"]:not([class*="button"]):not([class*="header"])',  // Элементы с "order" (кроме кнопок и заголовков)
      '[class*="trade"]:not([class*="button"]):not([class*="header"])',  // Элементы с "trade" (кроме кнопок и заголовков)
      '.table-row',               // Общие строки таблицы
      '[data-testid*="order"]',   // Элементы с "order" в data-testid
      '[data-testid*="trade"]',   // Элементы с "trade" в data-testid
      '.rc-table-row',            // React Component таблицы
      '[class*="list-item"]',     // Элементы списка
      '[class*="card"]',          // Карточки
      '.bybit-table-row',         // Специфичные классы Bybit
      '[class*="history"]',       // Элементы истории
      '[class*="transaction"]',   // Элементы транзакций
      '.table-body-row',          // Строки тела таблицы
      '[role="row"]',             // Элементы с ролью "row"
      'div[class*="row"]',        // Div с "row" в классе
      'div[class*="item"]',       // Div с "item" в классе
      '[class*="entry"]',         // Элементы записи
      '[class*="record"]'         // Элементы записи
    ];

    otherSelectors.forEach(selector => {
      const elements = document.querySelectorAll(selector);
      elements.forEach(element => {
        const elementText = element.textContent;
        if (this.isLikelyOrderElement(elementText)) {
          this.processOrderElement(element);
        }
      });
    });
  }

  isLikelyOrderElement(text) {
    const lowerText = text.toLowerCase();
    
    // Проверяем длину текста
    if (text.length < 30 || text.length > 500) {
      return false;
    }
    
    // Должна быть валюта
    const hasCurrency = lowerText.includes('usdt') || lowerText.includes('rub') || 
                       lowerText.includes('btc') || lowerText.includes('eth');
    
    // Должны быть числа с десятичными знаками (цены, количества)
    const hasDecimalNumbers = /\d+[.,]\d+/.test(text);
    
    // Должно быть направление сделки
    const hasDirection = lowerText.includes('продажа') || lowerText.includes('покупка') ||
                        lowerText.includes('buy') || lowerText.includes('sell');
    
    // Не должно быть элементов интерфейса
    const isNotInterface = !lowerText.includes('все все') && 
                           !lowerText.includes('экспорт экспорт') &&
                           !lowerText.includes('монета монета') &&
                           !lowerText.includes('тип тип') &&
                           !lowerText.includes('статус статус') &&
                           !lowerText.includes('купить / продать купить / продать');
    
    return hasCurrency && hasDecimalNumbers && hasDirection && isNotInterface;
  }

  processOrderRow(row) {
    try {
      // Ищем элементы с информацией об ордере
      const cells = row.querySelectorAll('td');
      if (cells.length < 5) return;

      // Извлекаем данные ордера
      const orderData = this.extractOrderData(cells);
      if (!orderData || this.processedOrders.has(orderData.order_id)) {
        return;
      }

      // Проверяем статус ордера
      if (this.isOrderCompleted(orderData.status)) {
        this.sendOrderToServer(orderData);
        this.processedOrders.add(orderData.order_id);
      }
    } catch (error) {
      console.error('Ошибка обработки строки ордера:', error);
    }
  }

  processOrderElement(element) {
    try {
      // Предварительная проверка элемента
      const elementText = element.textContent.toLowerCase();
      const textLength = elementText.length;
      
      // Игнорируем элементы интерфейса
      if (textLength < 20 || textLength > 1000) {
        return;
      }
      
      // Игнорируем повторяющиеся элементы интерфейса
      if (elementText.includes('все все') || elementText.includes('экспорт экспорт') ||
          elementText.includes('монета монета') || elementText.includes('тип тип') ||
          elementText.includes('статус статус') || elementText.includes('купить / продать купить / продать')) {
        return;
      }
      
      // Проверяем наличие валюты и других признаков ордера
      const hasCurrency = elementText.includes('usdt') || elementText.includes('btc') ||
          elementText.includes('eth') || elementText.includes('rub');
      const hasNumbers = /\d+[.,]\d+/.test(elementText);
      
      if (!hasCurrency || !hasNumbers) {
        return;
      }

      // Ищем данные внутри элемента
      const orderData = this.extractOrderDataFromElement(element);
      if (!orderData) {
        console.log('❌ Не удалось извлечь данные ордера из элемента');
        return;
      }
      
      if (this.processedOrders.has(orderData.order_id)) {
        console.log('⚠️ Ордер уже обработан:', orderData.order_id);
        return;
      }

      console.log('🔍 Проверяем статус ордера:', orderData.status);
      
      // Проверяем статус ордера
      if (this.isOrderCompleted(orderData.status)) {
        console.log('✅ Ордер готов к отправке на сервер:', orderData);
        this.sendOrderToServer(orderData);
        this.processedOrders.add(orderData.order_id);
      } else {
        console.log('❌ Ордер не прошел проверку статуса:', orderData.status);
      }
    } catch (error) {
      console.error('Ошибка обработки элемента ордера:', error);
    }
  }

  extractOrderData(cells) {
    try {
      // Адаптивная логика извлечения данных
      let orderId = '';
      let symbol = '';
      let side = '';
      let quantity = '';
      let price = '';
      let status = '';
      let executedAt = '';
      let fees = '0';

      // Ищем данные в ячейках
      cells.forEach((cell, index) => {
        const text = cell.textContent.trim();
        
        // Order ID (обычно в первой колонке или содержит длинный ID)
        if (index === 0 && text.match(/^[A-Z0-9]{8,}$/)) {
          orderId = text;
        } else if (text.match(/^[A-Z0-9]{8,}$/)) {
          orderId = text;
        }
        
        // Symbol (обычно содержит пару валют)
        if (text.match(/^[A-Z]{3,}\/[A-Z]{3,}$/)) {
          symbol = text;
        }
        
        // Side (Buy/Sell) - ищем в разных вариантах
        if (text.toLowerCase().includes('buy') || text.toLowerCase().includes('покупка')) {
          side = 'buy';
        } else if (text.toLowerCase().includes('sell') || text.toLowerCase().includes('продажа')) {
          side = 'sell';
        }
        
        // Status - расширенная логика
        if (text.toLowerCase().includes('filled') || text.toLowerCase().includes('completed') || 
            text.toLowerCase().includes('выполнен') || text.toLowerCase().includes('done')) {
          status = 'filled';
        } else if (text.toLowerCase().includes('canceled') || text.toLowerCase().includes('cancelled') ||
                   text.toLowerCase().includes('отменен') || text.toLowerCase().includes('отменён')) {
          status = 'canceled';
        } else if (text.toLowerCase().includes('pending') || text.toLowerCase().includes('ожидание')) {
          status = 'pending';
        } else if (text.toLowerCase().includes('appealed') || text.toLowerCase().includes('апелляция')) {
          status = 'appealed';
        }
        
        // Quantity и Price (числовые значения с разными форматами)
        if (text.match(/^\d+\.?\d*$/) || text.match(/^\d+,\d+$/)) {
          const numValue = parseFloat(text.replace(',', '.'));
          if (!quantity && numValue > 0 && numValue < 1000000) {
            quantity = numValue;
          } else if (!price && numValue > 0) {
            price = numValue;
          }
        }
        
        // Fees (комиссии)
        if (text.toLowerCase().includes('fee') || text.toLowerCase().includes('комиссия')) {
          const feeMatch = text.match(/\d+\.?\d*/);
          if (feeMatch) {
            fees = feeMatch[0];
          }
        }
        
        // Дата выполнения (ищем в разных форматах)
        if (text.match(/\d{2}\/\d{2}\/\d{4}/) || text.match(/\d{4}-\d{2}-\d{2}/)) {
          executedAt = text;
        }
      });

      // Проверяем, что получили достаточно данных
      if (!orderId || !symbol || !side) {
        return null;
      }

      // Если дата не найдена, используем текущую
      if (!executedAt) {
        executedAt = new Date().toISOString();
      }

      return {
        order_id: orderId,
        symbol,
        side,
        quantity: parseFloat(quantity) || 0,
        price: parseFloat(price) || 0,
        fees_usdt: parseFloat(fees) || 0,
        status: status || 'filled',
        executed_at: executedAt,
        platform: 'bybit',
        accountName: this.settings.accountName,
        employee_id: this.settings.employeeId
      };
    } catch (error) {
      console.error('Ошибка извлечения данных ордера:', error);
      return null;
    }
  }

  extractOrderDataFromElement(element) {
    try {
      const text = element.textContent || element.innerText || '';
      
      // Ищем все текстовые узлы и элементы внутри
      const allElements = [element, ...element.querySelectorAll('*')];
      const textParts = [];
      
      allElements.forEach(el => {
        if (el.textContent && el.textContent.trim()) {
          textParts.push(el.textContent.trim());
        }
      });

      // Объединяем все текстовые части
      const fullText = textParts.join(' ');
      
      console.log('Анализируем элемент:', fullText.substring(0, 200));
      
      let orderId = '';
      let symbol = '';
      let side = '';
      let quantity = '';
      let price = '';
      let status = '';
      let executedAt = '';
      let fees = '0';

      // Ищем Order ID (длинные числовые коды, специфичные для Bybit)
      const orderIdMatches = fullText.match(/\d{15,}/g); // Ищем числа длиной 15+ символов
      if (orderIdMatches && orderIdMatches.length > 0) {
        // Берем самый длинный ID (скорее всего это Order ID)
        orderId = orderIdMatches.reduce((a, b) => a.length > b.length ? a : b);
      } else {
        // Если не нашли длинный ID, ищем любой буквенно-цифровой код
        const alphaNumMatch = fullText.match(/[A-Z0-9]{8,}/);
        if (alphaNumMatch) {
          orderId = alphaNumMatch[0];
        }
      }

      // Ищем символ торговой пары (специально для Bybit RUB/USDT)
      if (fullText.includes('RUB') && fullText.includes('USDT')) {
        symbol = 'USDT/RUB'; // Продажа USDT за RUB
      } else {
        // Ищем обычные торговые пары
        const symbolMatch = fullText.match(/([A-Z]{3,})[\s\/\-]?([A-Z]{3,})/);
        if (symbolMatch) {
          symbol = symbolMatch[1] + '/' + symbolMatch[2];
        } else {
          // Ищем одиночные символы (например, просто USDT)
          const singleSymbolMatch = fullText.match(/\b([A-Z]{3,})\b/);
          if (singleSymbolMatch) {
            symbol = singleSymbolMatch[1] + '/USDT'; // По умолчанию добавляем USDT
          }
        }
      }

      // Ищем направление сделки (включая русские термины)
      if (fullText.toLowerCase().includes('buy') || fullText.toLowerCase().includes('покупка') || 
          fullText.toLowerCase().includes('long') || fullText.toLowerCase().includes('покупать')) {
        side = 'buy';
      } else if (fullText.toLowerCase().includes('sell') || fullText.toLowerCase().includes('продажа') || 
                 fullText.toLowerCase().includes('short') || fullText.toLowerCase().includes('продать')) {
        side = 'sell';
      }

      // Ищем статус (включая русские термины)
      if (fullText.toLowerCase().includes('filled') || fullText.toLowerCase().includes('completed') || 
          fullText.toLowerCase().includes('выполнен') || fullText.toLowerCase().includes('done') ||
          fullText.toLowerCase().includes('исполнен') || fullText.toLowerCase().includes('завершен') ||
          fullText.toLowerCase().includes('завершено')) {
        status = 'завершено';
      } else if (fullText.toLowerCase().includes('canceled') || fullText.toLowerCase().includes('cancelled') ||
                 fullText.toLowerCase().includes('отменен') || fullText.toLowerCase().includes('отменён')) {
        status = 'canceled';
      } else if (fullText.toLowerCase().includes('pending') || fullText.toLowerCase().includes('ожидание') ||
                 fullText.toLowerCase().includes('активен') || fullText.toLowerCase().includes('открыт')) {
        status = 'pending';
      } else if (fullText.toLowerCase().includes('appealed') || fullText.toLowerCase().includes('апелляция')) {
        status = 'appealed';
      } else {
        // Если статус не найден, считаем выполненным (если есть другие данные)
        status = 'завершено';
      }

      // Ищем числовые значения (специально для Bybit)
      console.log('Ищем числовые значения в тексте:', fullText);
      
      // Ищем цену в RUB (обычно число с запятой, например "83,75 RUB")
      const rubPriceMatch = fullText.match(/(\d+[,.]?\d*)\s*RUB/i);
      if (rubPriceMatch) {
        price = parseFloat(rubPriceMatch[1].replace(',', '.'));
        console.log('Найдена цена в RUB:', price);
      }
      
      // Ищем количество USDT (обычно число с запятой, например "137,0000 USDT")
      const usdtQuantityMatch = fullText.match(/(\d+[,.]?\d*)\s*USDT/i);
      if (usdtQuantityMatch) {
        quantity = parseFloat(usdtQuantityMatch[1].replace(',', '.'));
        console.log('Найдено количество USDT:', quantity);
      }
      
      // Если не нашли специфичные значения, ищем все числа
      if (!price || !quantity) {
        const allNumbers = fullText.match(/\d+[,.]?\d*/g);
        if (allNumbers) {
          const cleanNumbers = allNumbers
            .map(n => parseFloat(n.replace(',', '.')))
            .filter(n => !isNaN(n) && n > 0);
          
          console.log('Все найденные числа:', cleanNumbers);
          
          // Если не нашли цену, ищем число в диапазоне цен RUB/USDT (50-200)
          if (!price) {
            const possiblePrice = cleanNumbers.find(n => n >= 50 && n <= 200);
            if (possiblePrice) {
              price = possiblePrice;
              console.log('Найдена возможная цена:', price);
            }
          }
          
          // Если не нашли количество, ищем число больше 1 (но не цену)
          if (!quantity) {
            const possibleQuantity = cleanNumbers.find(n => n > 1 && n !== price);
            if (possibleQuantity) {
              quantity = possibleQuantity;
              console.log('Найдено возможное количество:', quantity);
            }
          }
          
          // Если всё ещё не нашли, берем первые два числа
          if (!quantity && cleanNumbers.length > 0) {
            quantity = cleanNumbers[0];
          }
          if (!price && cleanNumbers.length > 1) {
            price = cleanNumbers[1];
          }
        }
      }

      // Ищем дату (различные форматы)
      const dateMatch = fullText.match(/\d{2}\/\d{2}\/\d{4}|\d{4}-\d{2}-\d{2}|\d{2}\.\d{2}\.\d{4}|\d{2}-\d{2}-\d{2}/);
      if (dateMatch) {
        executedAt = dateMatch[0];
      } else {
        executedAt = new Date().toISOString();
      }

      // Если не нашли Order ID, создаем уникальный на основе данных
      if (!orderId && symbol && side) {
        orderId = `${symbol.replace('/', '')}_${side}_${Date.now()}`;
      }

      console.log('Извлеченные данные:', {
        orderId, symbol, side, quantity, price, status, executedAt
      });

      // Проверяем, что получили минимально необходимые данные
      if (!orderId || !symbol || !side) {
        console.log('Недостаточно данных для создания ордера');
        return null;
      }

      console.log('✅ Ордер прошел проверку данных, создаем объект ордера');

      const totalUsdt = quantity && price ? quantity * price : 0;

      return {
        order_id: orderId,
        employee_id: this.settings.employeeId,
        platform: 'bybit',
        accountName: this.settings.accountName,
        symbol: symbol,
        side: side,
        quantity: quantity || 0,
        price: price || 0,
        total_usdt: totalUsdt,
        fees_usdt: parseFloat(fees) || 0,
        status: status || 'filled',
        executed_at: executedAt
      };
    } catch (error) {
      console.error('Ошибка извлечения данных из элемента:', error);
      return null;
    }
  }

  isOrderCompleted(status) {
    const completedStatuses = ['filled', 'completed', 'executed', 'done', 'завершено', 'исполнен', 'выполнен'];
    const result = completedStatuses.some(s => status.toLowerCase().includes(s));
    console.log(`Проверка статуса "${status}": ${result ? 'ПРОШЕЛ' : 'НЕ ПРОШЕЛ'}`);
    return result;
  }

  checkOrderNotifications() {
    // Ищем уведомления о завершении ордеров
    const notifications = document.querySelectorAll('.notification, .toast, .alert, [role="alert"]');
    
    notifications.forEach(notification => {
      const text = notification.textContent.toLowerCase();
      if (text.includes('order') && (text.includes('filled') || text.includes('completed'))) {
        // Уведомление о завершении ордера
        this.handleOrderNotification(notification);
      }
    });
  }

  handleOrderNotification(notification) {
    // Извлекаем информацию из уведомления
    const text = notification.textContent;
    
    // Ищем Order ID в уведомлении
    const orderIdMatch = text.match(/order[:\s]+([A-Z0-9]{8,})/i);
    if (orderIdMatch) {
      const orderId = orderIdMatch[1];
      
      // Если ордер еще не обработан
      if (!this.processedOrders.has(orderId)) {
        // Получаем полную информацию об ордере
        this.fetchOrderDetails(orderId);
      }
    }
  }

  async fetchOrderDetails(orderId) {
    try {
      // Пытаемся найти ордер в таблице
      const orderRow = document.querySelector(`[data-order-id="${orderId}"], tr:has-text("${orderId}")`);
      if (orderRow) {
        const cells = orderRow.querySelectorAll('td');
        const orderData = this.extractOrderData(cells);
        if (orderData) {
          this.sendOrderToServer(orderData);
          this.processedOrders.add(orderId);
        }
      }
    } catch (error) {
      console.error('Ошибка получения деталей ордера:', error);
    }
  }

  async sendOrderToServer(orderData) {
    try {
      console.log('🚀 Отправляем ордер на сервер:', orderData);
      console.log('🔗 URL сервера:', `${this.settings.serverUrl}/api/orders`);
      
      // Проверяем, что URL сервера задан
      if (!this.settings.serverUrl) {
        throw new Error('URL сервера не задан в настройках расширения');
      }
      
      // Проверяем соединение с сервером
      console.log('🔍 Проверяем соединение с сервером...');
      
      const response = await fetch(`${this.settings.serverUrl}/api/orders`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(orderData)
      });

      console.log('📡 Ответ сервера - статус:', response.status);
      
      if (response.ok) {
        const responseData = await response.json();
        console.log('✅ Ордер успешно сохранен:', responseData);
        this.showSuccessNotification('Ордер сохранен в системе');
        return true;
      } else {
        const errorText = await response.text();
        console.error('❌ Ошибка сохранения ордера:', response.status, errorText);
        this.showErrorNotification(`Ошибка сохранения ордера: ${response.status}`);
        return false;
      }
    } catch (error) {
      console.error('💥 Ошибка отправки ордера:', error);
      
      // Детальная диагностика ошибки
      let errorMessage = 'Ошибка соединения с сервером';
      
      if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
        errorMessage = 'Сервер недоступен. Проверьте:\n1. Запущен ли сервер на ' + this.settings.serverUrl + '\n2. Правильность URL в настройках расширения\n3. Не блокирует ли браузер запросы';
        console.error('🔥 Сервер недоступен! Проверьте:');
        console.error('   1. Запущен ли сервер на:', this.settings.serverUrl);
        console.error('   2. Правильность URL в настройках расширения');
        console.error('   3. Не блокирует ли браузер запросы');
      } else if (error.name === 'TypeError' && error.message.includes('NetworkError')) {
        errorMessage = 'Сетевая ошибка. Проверьте интернет-соединение';
      } else if (error.message.includes('URL сервера не задан')) {
        errorMessage = 'Настройте URL сервера в расширении';
      }
      
      this.showErrorNotification(errorMessage);
      return false;
    }
  }

  showSuccessNotification(message) {
    this.showNotification(message, 'success');
  }

  showErrorNotification(message) {
    this.showNotification(message, 'error');
  }

  showNotification(message, type) {
    // Создаем уведомление
    const notification = document.createElement('div');
    notification.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      padding: 10px 15px;
      border-radius: 4px;
      color: white;
      font-weight: bold;
      z-index: 10000;
      background: ${type === 'success' ? '#28a745' : '#dc3545'};
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Удаляем через 3 секунды
    setTimeout(() => {
      if (notification.parentNode) {
        notification.parentNode.removeChild(notification);
      }
    }, 3000);
  }

  async loadExistingOrders(settings) {
    try {
      console.log('Начинаем загрузку существующих ордеров...');
      
      // Показываем уведомление о начале загрузки
      this.showNotification('Загружаем существующие ордера...', 'info');
      
      let allOrders = [];
      let processedElements = new Set();
      
      // 1. Ищем все таблицы с ордерами на странице
      const tableSelectors = [
        '[data-testid="order-table"]',
        '.order-table',
        '.orders-table',
        '.trades-table',
        '.history-table',
        'table[class*="order"]',
        'table[class*="trade"]',
        'table[class*="history"]',
        'table'
      ];
      
      for (const selector of tableSelectors) {
        const tables = document.querySelectorAll(selector);
        tables.forEach(table => {
          // Избегаем повторной обработки одного элемента
          if (processedElements.has(table)) return;
          processedElements.add(table);
          
          // Проверяем, что это таблица с ордерами (ищем ключевые слова)
          const tableText = table.textContent.toLowerCase();
          if (!tableText.includes('order') && !tableText.includes('trade') && 
              !tableText.includes('ордер') && !tableText.includes('сделка')) {
            return;
          }
          
          const rows = table.querySelectorAll('tr');
          console.log(`Обрабатываем таблицу с ${rows.length} строками`);
          
          rows.forEach((row, rowIndex) => {
            // Пропускаем заголовки
            if (rowIndex === 0) return;
            
            const cells = row.querySelectorAll('td');
            if (cells.length < 3) return; // Минимум 3 ячейки для ордера
            
            const orderData = this.extractOrderData(cells);
            if (orderData && this.isOrderCompleted(orderData.status)) {
              // Добавляем настройки пользователя
              orderData.employee_id = settings.employeeId;
              orderData.accountName = settings.accountName;
              orderData.platform = 'bybit';
              
              // Проверяем, что ордер еще не был обработан
              if (!this.processedOrders.has(orderData.order_id)) {
                allOrders.push(orderData);
              }
            }
          });
        });
      }

      // 2. Ищем div-элементы с ордерами (для современных веб-приложений)
      const divSelectors = [
        '.ant-table-row',           // Ant Design таблицы
        '[data-row-key]',           // Строки с data-row-key
        '.order-row',               // Строки ордеров
        '.trade-row',               // Строки сделок
        '.history-row',             // Строки истории
        '[class*="order"]',         // Любые элементы с "order" в классе
        '[class*="trade"]',         // Любые элементы с "trade" в классе
        '.table-row',               // Общие строки таблицы
        '[data-testid*="order"]',   // Элементы с "order" в data-testid
        '[data-testid*="trade"]',   // Элементы с "trade" в data-testid
        '.list-item',               // Элементы списка
        '[class*="row"]',           // Любые элементы с "row" в классе
        '.ant-table-tbody tr',      // Строки в tbody Ant Design
        '.rc-table-row',            // React Component таблицы
        '[class*="list-item"]',     // Элементы списка
        '[class*="card"]',          // Карточки
        '.bybit-table-row',         // Специфичные классы Bybit
        '[class*="history"]',       // Элементы истории
        '[class*="transaction"]',   // Элементы транзакций
        '.table-body-row',          // Строки тела таблицы
        '[role="row"]'              // Элементы с ролью "row"
      ];

      for (const selector of divSelectors) {
        const elements = document.querySelectorAll(selector);
        console.log(`Найдено ${elements.length} элементов для селектора: ${selector}`);
        
        elements.forEach(element => {
          // Избегаем повторной обработки одного элемента
          if (processedElements.has(element)) return;
          processedElements.add(element);
          
          // Проверяем, что элемент содержит данные об ордерах (улучшенная проверка)
          const elementText = element.textContent.toLowerCase();
          const textLength = elementText.length;
          
          // Игнорируем элементы интерфейса (кнопки, заголовки, фильтры)
          if (textLength < 20 || textLength > 1000) {
            return; // Слишком короткие или длинные элементы
          }
          
          // Игнорируем повторяющиеся элементы интерфейса
          if (elementText.includes('все все') || elementText.includes('экспорт экспорт') ||
              elementText.includes('монета монета') || elementText.includes('тип тип') ||
              elementText.includes('статус статус') || elementText.includes('купить / продать купить / продать')) {
            return;
          }
          
          // Проверяем наличие ключевых слов ордеров
          const hasOrderKeywords = elementText.includes('order') || elementText.includes('trade') || 
              elementText.includes('ордер') || elementText.includes('сделка') ||
              elementText.includes('покупка') || elementText.includes('продажа');
              
          const hasCurrency = elementText.includes('usdt') || elementText.includes('btc') ||
              elementText.includes('eth') || elementText.includes('rub');
              
          const hasNumbers = /\d+[.,]\d+/.test(elementText); // Числа с десятичными знаками
          
          const hasStatus = elementText.includes('исполнен') || elementText.includes('завершен') ||
              elementText.includes('filled') || elementText.includes('completed');
          
          // Элемент должен содержать валюту И (ключевые слова ИЛИ числа ИЛИ статус)
          if (!hasCurrency || !(hasOrderKeywords || hasNumbers || hasStatus)) {
            return;
          }
          
          const orderData = this.extractOrderDataFromElement(element);
          if (orderData) {
            console.log('📦 Извлечен ордер для загрузки:', orderData);
            
            if (this.isOrderCompleted(orderData.status)) {
              console.log('✅ Статус ордера подходит для загрузки');
              
              // Добавляем настройки пользователя
              orderData.employeeId = settings.employeeId;
              orderData.accountName = settings.accountName;
              orderData.platform = 'bybit';
              
              // Проверяем, что ордер еще не был обработан
              if (!this.processedOrders.has(orderData.orderId)) {
                allOrders.push(orderData);
                console.log('📝 Ордер добавлен в список для загрузки. Всего в списке:', allOrders.length);
              } else {
                console.log('⚠️ Ордер уже был обработан ранее:', orderData.orderId);
              }
            } else {
              console.log('❌ Статус ордера не подходит для загрузки:', orderData.status);
            }
          }
        });
      }
      
      console.log(`Найдено ${allOrders.length} ордеров для загрузки`);
      
      if (allOrders.length === 0) {
        // Дополнительная отладка - показываем что нашли на странице
        console.log('Отладка: ищем любые элементы с текстом, содержащим ключевые слова...');
        const allElements = document.querySelectorAll('*');
        let foundElements = 0;
        
        allElements.forEach(el => {
          const text = el.textContent.toLowerCase();
          if ((text.includes('order') || text.includes('trade') || text.includes('buy') || text.includes('sell') ||
               text.includes('продажа') || text.includes('покупка') || text.includes('usdt') || text.includes('rub')) && 
              text.length > 10 && text.length < 500) {
            console.log('Найден элемент с потенциальными данными ордера:', el.tagName, el.className, text.substring(0, 100));
            foundElements++;
          }
        });
        
        console.log(`Найдено ${foundElements} элементов с потенциальными данными ордеров`);
        
        // Специальная отладка для Bybit - ищем элементы с RUB или USDT
        console.log('Специальная отладка для Bybit:');
        const bybitElements = document.querySelectorAll('*');
        bybitElements.forEach(el => {
          const text = el.textContent;
          if (text.includes('RUB') || text.includes('USDT')) {
            console.log('Элемент с валютой:', el.tagName, el.className, text.substring(0, 150));
          }
        });
        
        this.showNotification(`Ордера не найдены на странице. Найдено ${foundElements} потенциальных элементов.`, 'error');
        return { success: false, error: `Ордера не найдены на странице. Найдено ${foundElements} потенциальных элементов.` };
      }
      
      // Отправляем ордера на сервер
      let successCount = 0;
      let errorCount = 0;
      
      for (const orderData of allOrders) {
        try {
          const response = await fetch(`${settings.serverUrl}/api/orders`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(orderData)
          });

          if (response.ok) {
            successCount++;
            // Добавляем в обработанные, чтобы избежать дублирования
            this.processedOrders.add(orderData.order_id);
          } else {
            errorCount++;
            console.error('Ошибка сохранения ордера:', orderData.order_id, response.status);
          }
        } catch (error) {
          errorCount++;
          console.error('Ошибка отправки ордера:', orderData.order_id, error);
        }
      }
      
      // Показываем результат
      if (successCount > 0) {
        this.showSuccessNotification(`Загружено ${successCount} ордеров!`);
        if (errorCount > 0) {
          this.showErrorNotification(`${errorCount} ордеров не удалось загрузить`);
        }
      } else {
        this.showErrorNotification('Не удалось загрузить ни одного ордера');
      }
      
      return { 
        success: successCount > 0, 
        count: successCount,
        total: allOrders.length,
        errors: errorCount
      };
      
    } catch (error) {
      console.error('Ошибка загрузки существующих ордеров:', error);
      this.showErrorNotification('Ошибка загрузки ордеров: ' + error.message);
      return { success: false, error: error.message };
    }
  }

  updateTracking() {
    if (this.observer) {
      this.observer.disconnect();
    }
    
    if (this.settings.trackingEnabled && this.settings.employeeId) {
      this.startTracking();
    }
  }
}

// Запускаем трекер
new BybitOrderTracker(); 