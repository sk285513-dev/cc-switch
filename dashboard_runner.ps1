# ==============================================================================
# [CRITICAL DEPENDENCY WARNING] Group 8: 系統啟動與本地工作站入口 (Startup & Entry)
# ------------------------------------------------------------------------------
# ⚠️ 系統最高入口點！絕對禁止 AI 擅自覆蓋、魔改或閹割這些啟動腳本。
# 修改前請務必參閱：PIPELINE_DEPENDENCIES.md
# ==============================================================================
#!/usr/bin/env pwsh
# dashboard_runner.ps1 — 在這個 PowerShell 視窗持續跑 dashboard
$env:PYTHONUTF8="1"
$env:PYTHONIOENCODING="utf-8"
Set-Location "C:\LocalAI_Workstation"

Write-Host "=== LexMind-Omni 進度儀表板 持續運行中 ===" -ForegroundColor Cyan
Write-Host "按 Ctrl+C 停止" -ForegroundColor Gray
Write-Host ""

while ($true) {
    try {
        python scripts\progress_dashboard.py
    } catch {
        Write-Host "[錯誤] $_" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "[自動重啟中，5 秒後重新整理...]" -ForegroundColor Yellow
    Start-Sleep -Seconds 5
}
