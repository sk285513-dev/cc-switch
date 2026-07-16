[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Write-Host "正在為您啟動 LexMind-Omni 三大核心監控視窗..." -ForegroundColor Cyan

# 1. 啟動真正的進度儀表板 (Dashboard)
Start-Process powershell -ArgumentList '-NoProfile', '-NoExit', '-ExecutionPolicy', 'Bypass', '-File', 'C:\LocalAI_Workstation\dashboard_runner.ps1'

# 2. 啟動真正的 KPI 監控 (KPI Runner)
Start-Process powershell -ArgumentList '-NoProfile', '-NoExit', '-ExecutionPolicy', 'Bypass', '-File', 'C:\LocalAI_Workstation\kpi_runner.ps1'

# 3. 啟動主工作流進度即時監控 (Workflow Log Tail)
Start-Process powershell -ArgumentList '-NoProfile', '-NoExit', '-Command', "Clear-Host; Write-Host '=== 正在即時監控主工作流進度 (workflow.log) ===' -ForegroundColor Yellow; Get-Content A:\logs\workflow.log -Encoding UTF8 -Wait -Tail 30"

Write-Host "啟動完成！" -ForegroundColor Green
