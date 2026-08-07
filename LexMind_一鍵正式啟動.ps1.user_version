﻿# ============================================================
#  LexMind-Omni  v2.1  (2026-07-21)  ASCII-safe edition
# ============================================================
$env:LEXMIND_ENV      = "v6_canary"
$env:LEXMIND_ENTERPRISE = "1"
$env:PYTHONUTF8       = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:LEXMIND_MANIFEST_DIR = "A:\manifests"
$env:LEXMIND_LOG_DIR = "A:\logs"
$env:LEXMIND_WORKDIR = "C:\LocalAI_Workstation"
$env:GOOGLE_CLOUD_PROJECT = "project-bbb51788-254b-4ec3-ad7"
$env:CLOUDSDK_CORE_PROJECT = "project-bbb51788-254b-4ec3-ad7"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

$ROOT = "C:\LocalAI_Workstation"
Set-Location $ROOT

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  LexMind-Omni  One-Click Startup  v2.1   " -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ── STEP 1: Kill stale processes ──────────────────────────────
Write-Host "[1/5] Killing stale processes (Nuclear Option)..." -ForegroundColor Yellow

try { taskkill /F /IM python.exe /T 2>&1 | Out-Null } catch {}
try { taskkill /F /IM pythonw.exe /T 2>&1 | Out-Null } catch {}
try { taskkill /F /IM node.exe /T 2>&1 | Out-Null } catch {}
try { taskkill /F /IM ffmpeg.exe /T 2>&1 | Out-Null } catch {}

# Fix Zombie Dashboard: Also kill any hidden PowerShell loops keeping dashboard/monitor scripts alive
Get-CimInstance Win32_Process -Filter "Name LIKE 'powershell%.exe' OR Name LIKE 'pwsh%.exe'" |
    Where-Object { $_.CommandLine -match "dashboard_runner" -or $_.CommandLine -match "workflow.log" -or $_.CommandLine -match "kpi_monitor" -or $_.CommandLine -match "watchdog" } |
    ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } catch {} }

Write-Host "  [OK] Killed all previous Python, Node, and FFmpeg processes." -ForegroundColor Green
Start-Sleep -Seconds 2

# ── STEP 1.5: Verify Code State Machine (patch_state_machine.ps1) ─
Write-Host "[1.5/5] Verifying Code Integrity..." -ForegroundColor Yellow
$verifyProcess = Start-Process powershell -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "$ROOT\patch_state_machine.ps1" -PassThru -Wait -WindowStyle Hidden
if ($verifyProcess.ExitCode -ne 0) {
    Write-Host "[ERROR] Code integrity verification failed! (Exit Code: $($verifyProcess.ExitCode))" -ForegroundColor Red
    Write-Host "Please check patch_state_machine.ps1 output." -ForegroundColor Red
    Write-Host "Aborting startup." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "  [OK] Code verification passed." -ForegroundColor Green

# ── STEP 2: Reset locks & quota ───────────────────────────────
Write-Host "[2/5] Resetting locks and quota..." -ForegroundColor Yellow

Remove-Item "$env:LEXMIND_MANIFEST_DIR\workflow.lock" -Force -ErrorAction SilentlyContinue
'{"exhausted_keys":[]}' | Out-File "$ROOT\config\quota_state.json" -Encoding UTF8 -NoNewline

Write-Host "  [OK] workflow.lock removed, quota_state.json reset" -ForegroundColor Green

# ── STEP 3: Background engines ────────────────────────────────
Write-Host "[3/5] Starting background engines..." -ForegroundColor Yellow

$wf = Get-CimInstance Win32_Process -Filter "Name LIKE 'python%.exe'" |
      Where-Object { $_.CommandLine -match "run_workflow" }
if ($wf) {
    Write-Host "  [SKIP] Workflow Engine already running  PID=$($wf.ProcessId)" -ForegroundColor DarkGray
} else {
    $env:PYTHONUTF8 = '1'
    $env:PYTHONIOENCODING = 'utf-8'
    Start-Process "C:\Python312\python.exe" `
        -ArgumentList "scripts_v6\run_workflow.py" `
        -WorkingDirectory $ROOT `
        -RedirectStandardOutput "A:\logs\run_workflow_stdout.log" `
        -RedirectStandardError "A:\logs\run_workflow_stderr.log" `
        -WindowStyle Hidden
    Write-Host "  [OK]   Workflow Engine started" -ForegroundColor Green
}

$wd = Get-CimInstance Win32_Process -Filter "Name LIKE 'python%.exe'" |
      Where-Object { $_.CommandLine -match "watchdog_monitor\.py" }
if ($wd) {
    Write-Host "  [SKIP] Watchdog already running  PID=$($wd.ProcessId)" -ForegroundColor DarkGray
} else {
    $env:PYTHONUTF8 = '1'
    $env:PYTHONIOENCODING = 'utf-8'
    Start-Process "C:\Python312\python.exe" `
        -ArgumentList "scripts_v6/watchdog_monitor.py" `
        -WorkingDirectory $ROOT `
        -RedirectStandardOutput "A:\logs\watchdog_monitor_stdout.log" `
        -RedirectStandardError "A:\logs\watchdog_monitor_stderr.log" `
        -WindowStyle Hidden
    Write-Host "  [OK]   Watchdog started" -ForegroundColor Green
}

$ah = Get-CimInstance Win32_Process -Filter "Name LIKE 'python%.exe'" |
      Where-Object { $_.CommandLine -match "auto_healer\.py" }
if ($ah) {
    Write-Host "  [SKIP] Auto Healer already running  PID=$($ah.ProcessId)" -ForegroundColor DarkGray
} else {
    $env:PYTHONUTF8 = '1'
    $env:PYTHONIOENCODING = 'utf-8'
    Start-Process "C:\Python312\python.exe" `
        -ArgumentList "scripts_v6/auto_healer.py" `
        -WorkingDirectory $ROOT `
        -RedirectStandardOutput "A:\logs\auto_healer_stdout.log" `
        -RedirectStandardError "A:\logs\auto_healer_stderr.log" `
        -WindowStyle Hidden
    Write-Host "  [OK]   Auto Healer started" -ForegroundColor Green
}

# ── STEP 4: Streamlit UI ──────────────────────────────────────
Write-Host "[4/5] Starting Streamlit UI..." -ForegroundColor Yellow

$st = Get-CimInstance Win32_Process -Filter "Name LIKE 'python%.exe'" |
      Where-Object { $_.CommandLine -match "streamlit" }
if ($st) {
    Write-Host "  [SKIP] Streamlit already running  PID=$($st.ProcessId)" -ForegroundColor DarkGray
} else {
    & "C:\Python312\pythonw.exe" "$ROOT\Launch_Isolated.py" powershell.exe -NoProfile -NoExit -ExecutionPolicy Bypass -Command "Clear-Host; Write-Host '=== 正在啟動企業級網頁控制面板 ===' -ForegroundColor Cyan; Set-Location '$ROOT'; streamlit run app_v6.py --server.port 8506 --server.headless true --theme.base='light'"
    Write-Host "  [OK]   Streamlit starting..." -ForegroundColor Green
    Start-Sleep -Seconds 5
    # 確保只精準開啟一個瀏覽器分頁
    try {
        Start-Process "http://localhost:8506" -ErrorAction SilentlyContinue
    } catch {}
}

# ── STEP 5: Monitor windows ───────────────────────────────────
Write-Host "[5/5] Starting monitor windows..." -ForegroundColor Yellow

# SRE Watchdog
$sre = Get-CimInstance Win32_Process -Filter "Name LIKE 'python%.exe'" |
       Where-Object { $_.CommandLine -match "sre_watchdog" }
if ($sre) {
    Write-Host "  [SKIP] SRE Watchdog already running  PID=$($sre.ProcessId)" -ForegroundColor DarkGray
} else {
    $env:PYTHONUTF8 = '1'
    $env:PYTHONIOENCODING = 'utf-8'
    Start-Process "C:\Python312\python.exe" `
        -ArgumentList "scripts_v6\sre_watchdog.py" `
        -WorkingDirectory $ROOT `
        -RedirectStandardOutput "A:\logs\sre_watchdog_stdout.log" `
        -RedirectStandardError "A:\logs\sre_watchdog_stderr.log" `
        -WindowStyle Hidden
    Write-Host "  [OK]   SRE Watchdog started in background" -ForegroundColor Green
}

# KPI Runner
$kpi = Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
       Where-Object { $_.CommandLine -match "kpi_runner" }
if ($kpi) {
    Write-Host "  [SKIP] KPI Monitor already running  PID=$($kpi.ProcessId)" -ForegroundColor DarkGray
} else {
    Start-Process powershell `
        -ArgumentList @("-ExecutionPolicy", "Bypass", "-File", "$ROOT\kpi_runner.ps1") `
        -WorkingDirectory $ROOT `
        -RedirectStandardOutput "A:\logs\kpi_runner.log" `
        -RedirectStandardError "A:\logs\kpi_runner_error.log" `
        -WindowStyle Hidden
    Write-Host "  [OK]   KPI Monitor started in background" -ForegroundColor Green
}

# Progress Dashboard
Write-Host "  [OK]   Starting Progress Dashboard window..." -ForegroundColor Green
& "C:\Python312\pythonw.exe" "$ROOT\Launch_Isolated.py" powershell.exe -NoProfile -NoExit -ExecutionPolicy Bypass -File "$ROOT\dashboard_runner.ps1"

# Workflow Log Monitor
Write-Host "  [OK]   Starting Workflow Log Monitor window..." -ForegroundColor Green
& "C:\Python312\pythonw.exe" "$ROOT\Launch_Isolated.py" powershell.exe -NoProfile -NoExit -ExecutionPolicy Bypass -Command "Clear-Host; Write-Host '=== 正在即時監控主工作流進度 (workflow.log) ===' -ForegroundColor Yellow; Get-Content A:\logs\workflow.log -Encoding UTF8 -Wait -Tail 30"

# ── Summary ───────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  All done! Check the following:           " -ForegroundColor Cyan
Write-Host "  1. Streamlit  -> http://localhost:8506   " -ForegroundColor Cyan
Write-Host "  (Watchdog and KPI Monitor are running in background)" -ForegroundColor Cyan
Write-Host "                                           " -ForegroundColor Cyan
Write-Host "  Crawler: python bot_ultimate_real_crawler.py" -ForegroundColor DarkYellow
Write-Host "  Or:      double-click Launch_Crawler_UI.vbs" -ForegroundColor DarkYellow
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Window will close in 5 seconds..." -ForegroundColor Gray
Start-Sleep -Seconds 5







