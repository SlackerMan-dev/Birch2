// Отладочный скрипт для тестирования извлечения данных на странице Bybit
// Вставьте этот код в консоль браузера на странице Bybit для отладки

function debugBybitOrderExtraction() {
  console.log('=== ОТЛАДКА ИЗВЛЕЧЕНИЯ ОРДЕРОВ BYBIT ===');
  
  // 1. Ищем все элементы с валютами
  console.log('\n1. Поиск элементов с валютами:');
  const currencyElements = [];
  document.querySelectorAll('*').forEach(el => {
    const text = el.textContent;
    if ((text.includes('RUB') || text.includes('USDT') || text.includes('BTC')) && 
        text.length > 5 && text.length < 200) {
      currencyElements.push({
        element: el,
        text: text,
        tag: el.tagName,
        className: el.className
      });
    }
  });
  
  console.log(`Найдено ${currencyElements.length} элементов с валютами`);
  currencyElements.slice(0, 10).forEach((item, index) => {
    console.log(`${index + 1}. ${item.tag}.${item.className}: ${item.text.substring(0, 100)}`);
  });
  
  // 2. Ищем элементы с ключевыми словами
  console.log('\n2. Поиск элементов с ключевыми словами:');
  const keywordElements = [];
  document.querySelectorAll('*').forEach(el => {
    const text = el.textContent.toLowerCase();
    if ((text.includes('продажа') || text.includes('покупка') || text.includes('buy') || text.includes('sell')) && 
        text.length > 10 && text.length < 300) {
      keywordElements.push({
        element: el,
        text: el.textContent,
        tag: el.tagName,
        className: el.className
      });
    }
  });
  
  console.log(`Найдено ${keywordElements.length} элементов с ключевыми словами`);
  keywordElements.slice(0, 10).forEach((item, index) => {
    console.log(`${index + 1}. ${item.tag}.${item.className}: ${item.text.substring(0, 100)}`);
  });
  
  // 3. Ищем строки таблиц
  console.log('\n3. Поиск строк таблиц:');
  const tableRows = document.querySelectorAll('tr, [role="row"], .ant-table-row');
  console.log(`Найдено ${tableRows.length} строк таблиц`);
  
  tableRows.forEach((row, index) => {
    if (index < 5) {
      console.log(`Строка ${index + 1}:`, row.tagName, row.className, row.textContent.substring(0, 100));
    }
  });
  
  // 4. Тестируем извлечение данных
  console.log('\n4. Тестирование извлечения данных:');
  
  function testExtractOrderData(element) {
    const text = element.textContent || '';
    const fullText = text;
    
    let orderId = '';
    let symbol = '';
    let side = '';
    let quantity = '';
    let price = '';
    let status = 'filled';
    
    // Order ID
    const orderIdMatch = fullText.match(/[A-Z0-9]{8,}/);
    if (orderIdMatch) {
      orderId = orderIdMatch[0];
    }
    
    // Symbol
    const symbolMatch = fullText.match(/([A-Z]{3,})[\s\/\-]?([A-Z]{3,})/);
    if (symbolMatch) {
      symbol = symbolMatch[1] + '/' + symbolMatch[2];
    } else {
      const singleSymbolMatch = fullText.match(/\b([A-Z]{3,})\b/);
      if (singleSymbolMatch) {
        symbol = singleSymbolMatch[1] + '/USDT';
      }
    }
    
    // Side
    if (fullText.toLowerCase().includes('buy') || fullText.toLowerCase().includes('покупка')) {
      side = 'buy';
    } else if (fullText.toLowerCase().includes('sell') || fullText.toLowerCase().includes('продажа')) {
      side = 'sell';
    }
    
    // Numbers
    const numbers = fullText.match(/[\d,]+\.?\d*/g);
    if (numbers) {
      const cleanNumbers = numbers.map(n => parseFloat(n.replace(/,/g, '')));
      const validNumbers = cleanNumbers.filter(n => n > 0 && n < 1000000000);
      
      if (validNumbers.length >= 1) {
        quantity = validNumbers[0];
      }
      if (validNumbers.length >= 2) {
        price = validNumbers[1];
      }
    }
    
    // Create order ID if missing
    if (!orderId && symbol && side) {
      orderId = `${symbol.replace('/', '')}_${side}_${Date.now()}`;
    }
    
    return {
      orderId, symbol, side, quantity, price, status,
      hasMinimalData: !!(orderId && symbol && side)
    };
  }
  
  // Тестируем на найденных элементах
  const testElements = [...currencyElements, ...keywordElements].slice(0, 5);
  testElements.forEach((item, index) => {
    console.log(`\nТест ${index + 1}:`);
    console.log('Элемент:', item.text.substring(0, 100));
    const result = testExtractOrderData(item.element);
    console.log('Результат:', result);
  });
  
  // 5. Поиск специфичных элементов Bybit
  console.log('\n5. Поиск специфичных элементов Bybit:');
  const bybitSelectors = [
    'tr',
    '.ant-table-row',
    '[data-row-key]',
    'tbody tr',
    '[class*="row"]',
    '[class*="item"]'
  ];
  
  bybitSelectors.forEach(selector => {
    const elements = document.querySelectorAll(selector);
    if (elements.length > 0) {
      console.log(`${selector}: найдено ${elements.length} элементов`);
      
      // Проверяем первые несколько элементов
      for (let i = 0; i < Math.min(3, elements.length); i++) {
        const el = elements[i];
        const text = el.textContent;
        if (text.includes('RUB') || text.includes('USDT') || text.includes('продажа') || text.includes('покупка')) {
          console.log(`  Элемент ${i + 1}:`, text.substring(0, 100));
        }
      }
    }
  });
  
  console.log('\n=== КОНЕЦ ОТЛАДКИ ===');
}

// Запуск отладки
debugBybitOrderExtraction(); 