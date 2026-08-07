# ==============================================================================
# [CRITICAL DEPENDENCY WARNING] Group 8: 系統啟動與本地工作站入口 (Startup & Entry)
# ------------------------------------------------------------------------------
# ⚠️ 系統最高入口點！絕對禁止 AI 擅自覆蓋、魔改或閹割這些啟動腳本。
# 修改前請務必參閱：PIPELINE_DEPENDENCIES.md
# ==============================================================================
﻿# ============================================================
#  修復版：完美繼承終極版的陣列寫法與防崩潰機制
# ============================================================
$env:PYTHONUTF8       = "1"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

$ROOT = "C:\LocalAI_Workstation"
Set-Location $ROOT

Write-Host "正在為您啟動 LexMind-Omni 三大核心監控視窗..." -ForegroundColor Cyan

# 1. 啟動真正的進度儀表板 (Dashboard)
Start-Process powershell -WindowStyle Normal -ArgumentList @("-NoProfile", "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "$ROOT\dashboard_runner.ps1") -WorkingDirectory $ROOT

# 2. 啟動真正的 KPI 監控 (KPI Runner)
Start-Process powershell -WindowStyle Normal -ArgumentList @("-NoProfile", "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "$ROOT\kpi_runner.ps1") -WorkingDirectory $ROOT

# 3. 啟動主工作流進度即時監控 (Workflow Log Tail)
Start-Process powershell -WindowStyle Normal -ArgumentList @("-NoProfile", "-NoExit", "-Command", "Clear-Host; Write-Host '=== 正在即時監控主工作流進度 (workflow.log) ===' -ForegroundColor Yellow; Get-Content A:\logs\workflow.log -Encoding UTF8 -Wait -Tail 30") -WorkingDirectory $ROOT

# 4. 啟動 LexMind-Omni 企業級網頁控制面板 (Streamlit)
Start-Process powershell -WindowStyle Normal -ArgumentList @("-NoProfile", "-NoExit", "-Command", "Clear-Host; Write-Host '=== 正在啟動企業級網頁控制面板 ===' -ForegroundColor Cyan; Set-Location '$ROOT'; streamlit run app.py --theme.base=`"light`"") -WorkingDirectory $ROOT

Write-Host "四大核心系統啟動中，等待 5 秒後將為您開啟瀏覽器..." -ForegroundColor Green
Start-Sleep -Seconds 5
Start-Process "http://localhost:8501"
