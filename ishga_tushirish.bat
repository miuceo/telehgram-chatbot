@echo off
chcp 65001 >nul
title Telegram AI Bot

echo =========================================================
echo               TELEGRAM AI BOT ISHGA TUSHMOQDA
echo =========================================================
echo.

:: Python mavjudligini tekshirish
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [XATO] Kompyuteringizda Python o'rnatilmagan yoki PATH ga qo'shilmagan!
    echo Iltimos, python.org saytidan Python'ni o'rnating.
    echo.
    pause
    exit /b
)

:: Botni yurgizish
echo Bot ishga tushirilmoqda...
echo Oynani yopmang! Bot ishlashi uchun ushbu oyna ochiq turishi kerak.
echo To'xtatish uchun: klaviaturada Ctrl + C tugmalarini bosing.
echo ---------------------------------------------------------
echo.

python bot.py

echo.
echo ---------------------------------------------------------
echo Bot to'xtadi.
pause
