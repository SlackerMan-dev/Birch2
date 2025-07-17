// Специальный скрипт для поиска ордеров на странице Bybit
// Запустите в консоли браузера на странице с ордерами

function findBybitOrders() {
  console.log('🔍 ПОИСК ОРДЕРОВ НА СТРАНИЦЕ BYBIT');
  console.log('=====================================');
  
  // Функция для проверки, похож ли элемент на ордер
  function isLikelyOrder(text) {
    const lowerText = text.toLowerCase();
    
    // Проверяем длину
    if (text.length < 30 || text.length > 500) {
      return false;
    }
    
    // Должна быть валюта
    const hasCurrency = lowerText.includes('usdt') || lowerText.includes('rub') || 
                       lowerText.includes('btc') || lowerText.includes('eth');
    
    // Должны быть числа с десятичными знаками
    const hasDecimalNumbers = /\d+[.,]\d+/.test(text);
    
    // Должно быть направление сделки
    const hasDirection = lowerText.includes('продажа') || lowerText.includes('покупка') ||
                        lowerText.includes('buy') || lowerText.includes('sell');
    
    // Не должно быть элементов интерфейса
    const isNotInterface = !lowerText.includes('все все') && 
                           !lowerText.includes('экспорт экспорт') &&
                           !lowerText.includes('монета монета') &&
                           !lowerText.includes('тип тип') &&
                           !lowerText.includes('статус статус');
    
    return hasCurrency && hasDecimalNumbers && hasDirection && isNotInterface;
  }
  
  // Функция для извлечения данных ордера
  function extractOrderInfo(text) {
    const lowerText = text.toLowerCase();
    
    // Направление
    let side = '';
    if (lowerText.includes('продажа') || lowerText.includes('sell')) {
      side = 'sell';
    } else if (lowerText.includes('покупка') || lowerText.includes('buy')) {
      side = 'buy';
    }
    
    // Валюта
    const currencies = text.match(/([A-Z]{3,})/g) || [];
    const symbol = currencies.length > 0 ? currencies[0] : '';
    
    // Числа
    const numbers = text.match(/[\d,]+\.?\d*/g) || [];
    const cleanNumbers = numbers.map(n => parseFloat(n.replace(/,/g, ''))).filter(n => !isNaN(n));
    
    return {
      side,
      symbol,
      numbers: cleanNumbers,
      text: text.substring(0, 100) + '...'
    };
  }
  
  // Поиск по приоритетным селекторам
  const prioritySelectors = [
    'tbody tr',
    '.ant-table-tbody > tr',
    'tr:not(:first-child)'
  ];
  
  let foundOrders = [];
  
  console.log('\n📊 ПОИСК В ПРИОРИТЕТНЫХ СЕЛЕКТОРАХ:');
  prioritySelectors.forEach(selector => {
    const elements = document.querySelectorAll(selector);
    console.log(`\n${selector}: найдено ${elements.length} элементов`);
    
    elements.forEach((element, index) => {
      const text = element.textContent;
      if (isLikelyOrder(text)) {
        const orderInfo = extractOrderInfo(text);
        foundOrders.push({
          selector,
          index,
          element,
          ...orderInfo
        });
        console.log(`  ✅ Ордер ${foundOrders.length}:`, orderInfo);
      }
    });
  });
  
  // Если не нашли в приоритетных, ищем в других
  if (foundOrders.length === 0) {
    console.log('\n📋 ПОИСК В ДОПОЛНИТЕЛЬНЫХ СЕЛЕКТОРАХ:');
    const otherSelectors = [
      '.ant-table-row',
      '[data-row-key]',
      '.order-row',
      '.trade-row',
      '.history-row',
      '[class*="order"]:not([class*="button"]):not([class*="header"])',
      '[role="row"]'
    ];
    
    otherSelectors.forEach(selector => {
      const elements = document.querySelectorAll(selector);
      if (elements.length > 0) {
        console.log(`\n${selector}: найдено ${elements.length} элементов`);
        
        elements.forEach((element, index) => {
          const text = element.textContent;
          if (isLikelyOrder(text)) {
            const orderInfo = extractOrderInfo(text);
            foundOrders.push({
              selector,
              index,
              element,
              ...orderInfo
            });
            console.log(`  ✅ Ордер ${foundOrders.length}:`, orderInfo);
          }
        });
      }
    });
  }
  
  // Результаты
  console.log('\n📈 РЕЗУЛЬТАТЫ ПОИСКА:');
  console.log(`Найдено ордеров: ${foundOrders.length}`);
  
  if (foundOrders.length > 0) {
    console.log('\n📋 СПИСОК НАЙДЕННЫХ ОРДЕРОВ:');
    foundOrders.forEach((order, index) => {
      console.log(`\n${index + 1}. ${order.selector}[${order.index}]`);
      console.log(`   Направление: ${order.side}`);
      console.log(`   Валюта: ${order.symbol}`);
      console.log(`   Числа: ${order.numbers.join(', ')}`);
      console.log(`   Текст: ${order.text}`);
    });
    
    // Показываем первый найденный элемент
    console.log('\n🔍 ПЕРВЫЙ НАЙДЕННЫЙ ЭЛЕМЕНТ:');
    console.log(foundOrders[0].element);
    
    // Предлагаем скопировать селектор
    console.log('\n💡 РЕКОМЕНДАЦИИ:');
    console.log(`Лучший селектор: ${foundOrders[0].selector}`);
    console.log('Добавьте этот селектор в начало массива orderSelectors в content.js');
    
  } else {
    console.log('\n❌ ОРДЕРА НЕ НАЙДЕНЫ');
    console.log('\n🔍 ДОПОЛНИТЕЛЬНАЯ ДИАГНОСТИКА:');
    
    // Ищем элементы с валютами
    const currencyElements = [];
    document.querySelectorAll('*').forEach(el => {
      const text = el.textContent;
      if ((text.includes('USDT') || text.includes('RUB')) && text.length > 10 && text.length < 300) {
        currencyElements.push({
          text: text.substring(0, 100),
          tag: el.tagName,
          className: el.className
        });
      }
    });
    
    console.log(`Найдено ${currencyElements.length} элементов с валютами:`);
    currencyElements.slice(0, 10).forEach((item, index) => {
      console.log(`${index + 1}. ${item.tag}.${item.className}: ${item.text}`);
    });
    
    // Ищем элементы с направлением сделки
    const directionElements = [];
    document.querySelectorAll('*').forEach(el => {
      const text = el.textContent.toLowerCase();
      if ((text.includes('продажа') || text.includes('покупка')) && text.length > 10 && text.length < 300) {
        directionElements.push({
          text: el.textContent.substring(0, 100),
          tag: el.tagName,
          className: el.className
        });
      }
    });
    
    console.log(`\nНайдено ${directionElements.length} элементов с направлением сделки:`);
    directionElements.slice(0, 10).forEach((item, index) => {
      console.log(`${index + 1}. ${item.tag}.${item.className}: ${item.text}`);
    });
  }
  
  console.log('\n=====================================');
  console.log('🔍 ПОИСК ЗАВЕРШЕН');
  
  return foundOrders;
}

// Запуск поиска
const orders = findBybitOrders(); 