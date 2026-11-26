@echo off
title DashNET Local Server Launcher
mode con: cols=60 lines=20
color 0A
cls

echo.
echo    =========================================
echo           DashNET - Local Server
echo    =========================================
echo.

:: ------------------------------------------------
:: 1. المحاولة باستخدام Python (الطريقة الأكثر شيوعاً)
:: ------------------------------------------------
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo    [+] Found Python. Starting server...
    echo.
    echo    Server: http://localhost:8000
    echo.
    echo    [Press Ctrl+C to close]
    python -m http.server 8000
    pause
    exit
)

:: ------------------------------------------------
:: 2. المحاولة باستخدام Python Launcher
:: ------------------------------------------------
py --version >nul 2>&1
if %errorlevel% equ 0 (
    echo    [+] Found Python (py). Starting server...
    echo.
    echo    Server: http://localhost:8000
    echo.
    echo    [Press Ctrl+C to close]
    py -m http.server 8000
    pause
    exit
)

:: ------------------------------------------------
:: 3. المحاولة باستخدام PHP
:: ------------------------------------------------
php -v >nul 2>&1
if %errorlevel% equ 0 (
    echo    [+] Found PHP. Starting server...
    echo.
    echo    Server: http://localhost:8000
    echo.
    echo    [Press Ctrl+C to close]
    php -S localhost:8000
    pause
    exit
)

:: ------------------------------------------------
:: 4. المحاولة باستخدام Node.js (http-server)
:: ------------------------------------------------
call npm -v >nul 2>&1
if %errorlevel% equ 0 (
    echo    [+] Found Node.js. Installing http-server...
    echo.
    echo    Server: http://localhost:8000
    echo.
    npx http-server -p 8000 -c-1 -o
    pause
    exit
)

:: ------------------------------------------------
:: في حال الفشل
:: ------------------------------------------------
cls
color 0C
echo.
echo    [!] ERROR: No suitable runtime found.
echo    =========================================
echo    Please install Python to run the server.
echo    Download: https://www.python.org/downloads/
echo.
pause