// Background script для расширения
chrome.runtime.onInstalled.addListener(() => {
  console.log('Bybit Order Tracker установлен');
});

// Обработка сообщений от content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'orderCompleted') {
    console.log('Ордер завершен:', message.orderData);
    // Здесь можно добавить дополнительную логику
  }
});

// Обработка обновления вкладок
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url && tab.url.includes('bybit.com')) {
    // Страница Bybit загружена, можно инициализировать трекинг
    console.log('Bybit страница загружена');
  }
}); 