@echo off
chcp 65001 >nul
cd /d "%~dp0"
title LexMind 一鍵本機部署啟動器
echo ====================================================================
echo 🚀 歡迎使用 LexMind-Omni 離線/本機安全 AI 法律工作站一鍵啟動器！
echo.
echo ⚠️ 正在以安全繞過模式（Bypass）執行本地核心部署指令碼 (setup_lexmind.ps1)...
echo ====================================================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_lexmind.ps1"
echo.
echo ====================================================================
echo ✨ 部署與安裝程序執行完畢！若看見 Streamlit 連線訊息，請在瀏覽器開啟該本機網址即可！
echo ====================================================================
pause
