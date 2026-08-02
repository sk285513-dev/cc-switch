# 啟動設定精靈.ps1
# 設定主控台編碼為 UTF-8 確保中文顯示正常
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "正在啟動 LexMind 互動式設定與資安守護精靈..." -ForegroundColor Cyan
Write-Host "請稍候..." -ForegroundColor DarkGray

# 切換到腳本目錄
Set-Location -Path "C:\LocalAI_Workstation"

# 使用 python 執行精靈
python .\scripts\setup_wizard.py

Write-Host "
程式已結束。" -ForegroundColor Green
Read-Host "按下 Enter 鍵關閉視窗"
