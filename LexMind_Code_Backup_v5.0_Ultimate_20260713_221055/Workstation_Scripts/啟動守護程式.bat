@echo off
chcp 65001 > nul
TITLE LexMind-Omni Watchdog
echo ============================================
echo  LexMind-Omni 自動守護程式
echo  每 60 秒檢查 run_workflow.py 是否存活
echo  日誌位置: A:\logs\watchdog.log
echo ============================================

cd /d C:\LocalAI_Workstation

:LOOP
python scripts\watchdog.py
echo [%TIME%] watchdog.py 意外退出，5 秒後重新啟動...
timeout /t 5 /nobreak > nul
goto LOOP
