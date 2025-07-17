<?php
// Конфигурация базы данных
define('DB_HOST', 'localhost');
define('DB_NAME', 'accounting_system');
define('DB_USER', 'your_username');
define('DB_PASS', 'your_password');

// Пароли для входа
define('APP_PASSWORD', '76005203');
define('ADMIN_PASSWORD', 'blalala2');

// Настройки приложения
define('APP_NAME', 'Таблица бухгалтерии');
define('APP_VERSION', '1.0.0');
define('TIMEZONE', 'Europe/Moscow');

// Устанавливаем часовой пояс
date_default_timezone_set(TIMEZONE);

// Функция для подключения к базе данных
function getDbConnection() {
    try {
        $pdo = new PDO(
            "mysql:host=" . DB_HOST . ";dbname=" . DB_NAME . ";charset=utf8", 
            DB_USER, 
            DB_PASS
        );
        $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        return $pdo;
    } catch(PDOException $e) {
        die("Ошибка подключения к базе данных: " . $e->getMessage());
    }
}

// Функция для проверки авторизации
function isAuthorized() {
    session_start();
    return isset($_SESSION['authorized']) && $_SESSION['authorized'] === true;
}

// Функция для авторизации
function login($password) {
    if ($password === APP_PASSWORD) {
        session_start();
        $_SESSION['authorized'] = true;
        return true;
    }
    return false;
}

// Функция для выхода
function logout() {
    session_start();
    session_destroy();
}
?> 