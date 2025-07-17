// Управление настройками расширения
document.addEventListener('DOMContentLoaded', function() {
  const serverUrlInput = document.getElementById('serverUrl');
  const employeeIdSelect = document.getElementById('employeeId');
  const accountNameInput = document.getElementById('accountName');
  const trackingEnabledCheckbox = document.getElementById('trackingEnabled');
  const saveButton = document.getElementById('saveSettings');
  const testButton = document.getElementById('testConnection');
  const loadOrdersButton = document.getElementById('loadExistingOrders');
  const statusDiv = document.getElementById('status');

  // Загружаем сохраненные настройки
  loadSettings();
  
  // Загружаем список сотрудников
  loadEmployees();

  // Обработчики событий
  saveButton.addEventListener('click', saveSettings);
  testButton.addEventListener('click', testConnection);
  loadOrdersButton.addEventListener('click', loadExistingOrders);

  async function loadSettings() {
    try {
      const result = await chrome.storage.sync.get([
        'serverUrl',
        'employeeId',
        'accountName',
        'trackingEnabled'
      ]);
      
      serverUrlInput.value = result.serverUrl || 'http://localhost:5000';
      employeeIdSelect.value = result.employeeId || '';
      accountNameInput.value = result.accountName || '';
      trackingEnabledCheckbox.checked = result.trackingEnabled || false;
    } catch (error) {
      showStatus('Ошибка загрузки настроек: ' + error.message, 'error');
    }
  }

  async function loadEmployees() {
    try {
      const serverUrl = serverUrlInput.value || 'http://localhost:5000';
      const response = await fetch(`${serverUrl}/api/employees`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const employees = await response.json();
      
      // Очищаем список
      employeeIdSelect.innerHTML = '<option value="">Выберите сотрудника...</option>';
      
      // Добавляем сотрудников
      employees.forEach(employee => {
        const option = document.createElement('option');
        option.value = employee.id;
        option.textContent = `${employee.name} (${employee.telegram})`;
        employeeIdSelect.appendChild(option);
      });
    } catch (error) {
      showStatus('Ошибка загрузки сотрудников: ' + error.message, 'error');
    }
  }

  async function saveSettings() {
    try {
      const settings = {
        serverUrl: serverUrlInput.value,
        employeeId: employeeIdSelect.value,
        accountName: accountNameInput.value,
        trackingEnabled: trackingEnabledCheckbox.checked
      };

      await chrome.storage.sync.set(settings);
      
      // Отправляем сообщение в content script
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab) {
        await chrome.tabs.sendMessage(tab.id, {
          action: 'updateSettings',
          settings: settings
        });
      }
      
      showStatus('Настройки сохранены!', 'success');
    } catch (error) {
      showStatus('Ошибка сохранения: ' + error.message, 'error');
    }
  }

  async function testConnection() {
    try {
      const serverUrl = serverUrlInput.value;
      showStatus('Проверяем соединение...', 'info');
      
      const response = await fetch(`${serverUrl}/api/employees`);
      
      if (response.ok) {
        showStatus('Соединение успешно!', 'success');
      } else {
        showStatus(`Ошибка соединения: HTTP ${response.status}`, 'error');
      }
    } catch (error) {
      showStatus('Ошибка соединения: ' + error.message, 'error');
    }
  }

  function showStatus(message, type) {
    statusDiv.textContent = message;
    statusDiv.className = `status ${type}`;
    statusDiv.style.display = 'block';
    
    setTimeout(() => {
      statusDiv.style.display = 'none';
    }, 3000);
  }

  async function loadExistingOrders() {
    try {
      const serverUrl = serverUrlInput.value;
      const employeeId = employeeIdSelect.value;
      const accountName = accountNameInput.value;
      
      if (!employeeId) {
        showStatus('Сначала выберите сотрудника!', 'error');
        return;
      }
      
      if (!accountName) {
        showStatus('Укажите название аккаунта!', 'error');
        return;
      }
      
      showStatus('Загружаем существующие ордера...', 'info');
      
      // Отправляем сообщение в content script для загрузки ордеров
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab) {
        const response = await chrome.tabs.sendMessage(tab.id, {
          action: 'loadExistingOrders',
          settings: {
            serverUrl,
            employeeId,
            accountName
          }
        });
        
        if (response && response.success) {
          showStatus(`Загружено ${response.count} ордеров!`, 'success');
        } else {
          showStatus('Ошибка загрузки ордеров: ' + (response?.error || 'Неизвестная ошибка'), 'error');
        }
      } else {
        showStatus('Откройте страницу Bybit для загрузки ордеров', 'error');
      }
    } catch (error) {
      showStatus('Ошибка загрузки: ' + error.message, 'error');
    }
  }

  // Обновляем список сотрудников при изменении URL сервера
  serverUrlInput.addEventListener('blur', loadEmployees);
}); 