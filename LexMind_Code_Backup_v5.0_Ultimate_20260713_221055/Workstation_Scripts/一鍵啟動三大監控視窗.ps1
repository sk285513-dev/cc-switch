# 設定主視窗的字元集為 UTF-8 避免中文亂碼
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "正在為您啟動 LexMind-Omni 三大核心監控視窗..." -ForegroundColor Cyan

# 1. 啟動主工作流進度監控 (Workflow)
Start-Process powershell -ArgumentList '-NoProfile', '-NoExit', '-Command', "`$Host.UI.RawUI.BackgroundColor = 'Black'; `$Host.UI.RawUI.ForegroundColor = 'Green'; Clear-Host; Write-Host '=== 正在即時監控主工作流進度 (workflow.log) ===' -ForegroundColor Yellow; Get-Content A:\logs\workflow.log -Encoding UTF8 -Wait -Tail 30"

# 2. 啟動看門狗健康監控 (Watchdog)
Start-Process powershell -ArgumentList '-NoProfile', '-NoExit', '-Command', "`$Host.UI.RawUI.BackgroundColor = 'DarkBlue'; `$Host.UI.RawUI.ForegroundColor = 'White'; Clear-Host; Write-Host '=== 正在即時監控系統守護狀態 (watchdog.log) ===' -ForegroundColor Yellow; Get-Content A:\logs\watchdog.log -Encoding UTF8 -Wait -Tail 20"

# 3. 啟動 KPI 與並發效能監控 (KPI Monitor)
Start-Process powershell -ArgumentList '-NoProfile', '-NoExit', '-Command', "`$Host.UI.RawUI.BackgroundColor = 'DarkRed'; `$Host.UI.RawUI.ForegroundColor = 'White'; Clear-Host; Write-Host '=== 正在即時監控 KPI 產能與並發安全 (kpi_monitor.log) ===' -ForegroundColor Yellow; Get-Content A:\logs\kpi_monitor.log -Encoding UTF8 -Wait -Tail 20"

Write-Host "啟動完成！" -ForegroundColor Green
