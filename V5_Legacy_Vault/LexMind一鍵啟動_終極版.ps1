# ==============================================================================
# [CRITICAL DEPENDENCY WARNING] Group 8: 系統啟動與本地工作站入口 (Startup & Entry)
# ------------------------------------------------------------------------------
# ⚠️ 系統最高入口點！絕對禁止 AI 擅自覆蓋、魔改或閹割這些啟動腳本。
# 修改前請務必參閱：PIPELINE_DEPENDENCIES.md
# ==============================================================================
# ============================================================
#  LexMind-Omni  v2.1  (2026-07-21)  ASCII-safe edition
# ============================================================
$env:PYTHONUTF8       = "1"
$env:PYTHONIOENCODING = "utf-8"
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
Write-Host "[1/5] Killing stale processes..." -ForegroundColor Yellow

$targets = @("run_workflow","watchdog","progress_dashboard",
             "streamlit","kpi_monitor","sre_watchdog")
$killed  = 0

Get-CimInstance Win32_Process -Filter "Name LIKE 'python%.exe'" | ForEach-Object {
    $cmd = $_.CommandLine
    foreach ($t in $targets) {
        if ($cmd -match [regex]::Escape($t)) {
            Write-Host "  [KILL] PID=$($_.ProcessId)  $t" -ForegroundColor Red
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
            $killed++
            break
        }
    }
}
Get-CimInstance Win32_Process -Filter "Name='node.exe'" | ForEach-Object {
    if ($_.CommandLine -match "streamlit") {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        $killed++
    }
}

if ($killed -eq 0) {
    Write-Host "  (no stale processes found)" -ForegroundColor Gray
} else {
    Write-Host "  Killed $killed process(es)" -ForegroundColor Green
}
Start-Sleep -Seconds 2

# ── STEP 2: Reset locks & quota ───────────────────────────────
Write-Host "[2/5] Resetting locks and quota..." -ForegroundColor Yellow

Remove-Item "A:\manifests\workflow.lock" -Force -ErrorAction SilentlyContinue
'{"exhausted_keys":[]}' | Out-File "$ROOT\config\quota_state.json" -Encoding UTF8 -NoNewline

Write-Host "  [OK] workflow.lock removed, quota_state.json reset" -ForegroundColor Green

# ── STEP 3: Background engines ────────────────────────────────
Write-Host "[3/5] Starting background engines..." -ForegroundColor Yellow

$wf = Get-CimInstance Win32_Process -Filter "Name LIKE 'python%.exe'" |
      Where-Object { $_.CommandLine -match "run_workflow" }
if ($wf) {
    Write-Host "  [SKIP] Workflow Engine already running  PID=$($wf.ProcessId)" -ForegroundColor DarkGray
} else {
    Start-Process "pythonw" `
        -ArgumentList "scripts/run_workflow.py" `
        -WorkingDirectory $ROOT `
        -WindowStyle Hidden
    Write-Host "  [OK]   Workflow Engine started" -ForegroundColor Green
}

$wd = Get-CimInstance Win32_Process -Filter "Name LIKE 'python%.exe'" |
      Where-Object { $_.CommandLine -match "watchdog\.py" }
if ($wd) {
    Write-Host "  [SKIP] Watchdog already running  PID=$($wd.ProcessId)" -ForegroundColor DarkGray
} else {
    Start-Process "pythonw" `
        -ArgumentList "scripts/watchdog.py" `
        -WorkingDirectory $ROOT `
        -WindowStyle Hidden
    Write-Host "  [OK]   Watchdog started" -ForegroundColor Green
}

# ── STEP 4: Streamlit UI ──────────────────────────────────────
Write-Host "[4/5] Starting Streamlit UI..." -ForegroundColor Yellow

$st = Get-CimInstance Win32_Process -Filter "Name LIKE 'python%.exe'" |
      Where-Object { $_.CommandLine -match "streamlit" }
if ($st) {
    Write-Host "  [SKIP] Streamlit already running  PID=$($st.ProcessId)" -ForegroundColor DarkGray
} else {
    Start-Process powershell `
        -WindowStyle Normal `
        -ArgumentList @(
            "-NoExit","-ExecutionPolicy","Bypass","-Command",
            "`$env:PYTHONUTF8='1'; Set-Location '$ROOT'; python -m streamlit run app.py --server.port 8501"
        ) `
        -WorkingDirectory $ROOT
    Write-Host "  [OK]   Streamlit starting... waiting for it to open browser" -ForegroundColor Green
    Start-Sleep -Seconds 5
    # Start-Process "http://localhost:8501" # Removed to prevent double tab opening
}

# ── STEP 5: Monitor windows ───────────────────────────────────
Write-Host "[5/5] Starting monitor windows..." -ForegroundColor Yellow

# SRE Watchdog
$sre = Get-CimInstance Win32_Process -Filter "Name LIKE 'python%.exe'" |
       Where-Object { $_.CommandLine -match "sre_watchdog" }
if ($sre) {
    Write-Host "  [SKIP] SRE Watchdog already running  PID=$($sre.ProcessId)" -ForegroundColor DarkGray
} else {
    Start-Process powershell `
        -WindowStyle Normal `
        -ArgumentList @(
            "-NoExit","-ExecutionPolicy","Bypass","-Command",
            "`$env:PYTHONUTF8='1'; Set-Location '$ROOT'; python scripts\sre_watchdog.py"
        ) `
        -WorkingDirectory $ROOT
    Write-Host "  [OK]   SRE Watchdog opened" -ForegroundColor Green
}

# KPI Runner
$kpi = Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
       Where-Object { $_.CommandLine -match "kpi_runner" }
if ($kpi) {
    Write-Host "  [SKIP] KPI Monitor already running  PID=$($kpi.ProcessId)" -ForegroundColor DarkGray
} else {
    Start-Process powershell `
        -WindowStyle Normal `
        -ArgumentList @("-NoExit","-ExecutionPolicy","Bypass","-File","$ROOT\kpi_runner.ps1") `
        -WorkingDirectory $ROOT
    Write-Host "  [OK]   KPI Monitor opened" -ForegroundColor Green
}

# Progress Dashboard
$db = Get-CimInstance Win32_Process -Filter "Name LIKE 'python%.exe'" |
      Where-Object { $_.CommandLine -match "progress_dashboard" }
if ($db) {
    Write-Host "  [SKIP] Progress Dashboard already running  PID=$($db.ProcessId)" -ForegroundColor DarkGray
} else {
    Start-Process powershell `
        -WindowStyle Normal `
        -ArgumentList @(
            "-NoExit","-ExecutionPolicy","Bypass","-Command",
            "`$env:PYTHONUTF8='1'; Set-Location '$ROOT'; python scripts_v6\progress_dashboard.py"
        ) `
        -WorkingDirectory $ROOT
    Write-Host "  [OK]   Progress Dashboard opened" -ForegroundColor Green
}

# ── Summary ───────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  All done! Check the following:           " -ForegroundColor Cyan
Write-Host "  1. Streamlit  -> http://localhost:8501   " -ForegroundColor Cyan
Write-Host "  2. SRE Watchdog  (PowerShell window)     " -ForegroundColor Cyan
Write-Host "  3. KPI Monitor   (PowerShell window)     " -ForegroundColor Cyan
Write-Host "  4. Dashboard     (PowerShell window)     " -ForegroundColor Cyan
Write-Host "                                           " -ForegroundColor Cyan
Write-Host "  Crawler: python bot_ultimate_real_crawler.py" -ForegroundColor DarkYellow
Write-Host "  Or:      double-click Launch_Crawler_UI.vbs" -ForegroundColor DarkYellow
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Window will close in 5 seconds..." -ForegroundColor Gray
Start-Sleep -Seconds 5
