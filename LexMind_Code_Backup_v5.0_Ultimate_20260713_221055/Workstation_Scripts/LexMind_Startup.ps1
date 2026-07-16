# ══════════════════════════════════════════════════════════════
# LexMind-Omni 一鍵啟動腳本 v2.0 (最終完美修正版)
# 儲存於: C:\LocalAI_Workstation\LexMind_Startup.ps1
# 開機自動執行 — 由 Windows 工作排程器或 VBS 呼叫
# ══════════════════════════════════════════════════════════════

$env:PYTHONUTF8       = "1"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$PYTHON       = "C:\Python312\python.exe"
$WORKDIR      = "C:\LocalAI_Workstation"
$LEXMIND_UI   = "C:\Users\temp\antigravity\LexMind-Omni-法律實務-AI-工作站"
$LOCK_FILE    = "A:\manifests\workflow.lock"
$QUOTA_STATE  = "$WORKDIR\config\quota_state.json"
$LOG          = "A:\logs\startup.log"

# ── 確保日誌目錄存在 ──────────────────────────────────────────
New-Item -ItemType Directory -Force -Path "A:\logs"     | Out-Null
New-Item -ItemType Directory -Force -Path "A:\manifests" | Out-Null

function Write-Log ($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$ts $msg" | Add-Content -Path $LOG -Encoding UTF8
    Write-Host "$ts $msg"
}

Write-Log "=== LexMind-Omni 啟動序列開始 ==="

# ── 1. 清除殘留鎖定檔與重置 Quota 狀態 ──────────────────────
Write-Log "[INIT] 清除 workflow.lock 與 quota_state..."
Remove-Item $LOCK_FILE -Force -ErrorAction SilentlyContinue
'{"exhausted_keys":[]}' | Out-File $QUOTA_STATE -Encoding UTF8 -NoNewline

# ── 2. 進度儀表板 ─────────────────────────────────────────────
Write-Log "[DASH] 啟動進度儀表板..."
Start-Process powershell -WindowStyle Normal -ArgumentList `
    "-NoExit", "-ExecutionPolicy", "Bypass", `
    "-File", "$WORKDIR\dashboard_runner.ps1"

# ── 3. KPI 自動監控（每 5 分鐘） ─────────────────────────────
Write-Log "[KPI] 啟動 KPI 監控..."
Start-Process powershell -WindowStyle Normal -ArgumentList `
    "-NoExit", "-ExecutionPolicy", "Bypass", `
    "-File", "$WORKDIR\kpi_runner.ps1"

# ── 4. Watchdog（管理 run_workflow.py 的守護進程）────────────
$existingWatchdog = Get-WmiObject Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match "watchdog\.py" }

if (-not $existingWatchdog) {
    Write-Log "[WATCHDOG] 啟動 Watchdog 守護進程..."
    Start-Process $PYTHON `
        -ArgumentList "$WORKDIR\scripts\watchdog.py" `
        -WorkingDirectory $WORKDIR `
        -WindowStyle Hidden
    Write-Log "[WATCHDOG] 已啟動，將由 Watchdog 自動管理 run_workflow.py"
} else {
    Write-Log "[WATCHDOG] 已在執行中 (PID=$($existingWatchdog.ProcessId))"
}

# ── 5. LexMind-Omni 前端 Node.js 伺服器 ─────────────────────
$existingNode = Get-WmiObject Win32_Process -Filter "Name='node.exe'" |
    Where-Object { $_.CommandLine -match "server\.ts|server\.cjs" }

if (-not $existingNode) {
    Write-Log "[UI] 啟動 LexMind-Omni UI 伺服器 (npm run dev)..."
    Start-Process powershell -WindowStyle Normal -ArgumentList `
        "-NoExit", "-ExecutionPolicy", "Bypass", `
        "-Command", "npm run dev" `
        -WorkingDirectory $LEXMIND_UI
    Write-Log "[UI] UI 伺服器已啟動"
} else {
    Write-Log "[UI] UI 伺服器已在執行中"
}

Write-Log "=== LexMind-Omni 啟動序列完成 ==="
