# ==============================================================================
#  LexMind-Omni V6.1  一鍵沙盒驗證啟動版 (Sandbox All-in-One Launcher)
#  [Fix1] 改用 python.exe + RedirectStandardOutput -> 消滅 WinError 10106
#  [Fix2] UI 入口改為正確的 web_dashboard.py
#  [Fix3] 所有路徑統一指向 _v6 隔離區
#  [Fix4] 移除 patch_state_machine.ps1 的 hard-gate 阻斷
# ==============================================================================

$env:LEXMIND_ENV          = "v6_canary"
$env:LEXMIND_ENTERPRISE   = "1"
$env:PYTHONUTF8           = "1"
$env:PYTHONIOENCODING     = "utf-8"
$env:LEXMIND_MANIFEST_DIR = "A:\manifests_v6"
$env:LEXMIND_LOG_DIR      = "A:\logs_v6"
$env:LEXMIND_WORKDIR      = "C:\LocalAI_Workstation\scripts_recovery_test"
[Console]::OutputEncoding  = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

$ROOT     = "C:\LocalAI_Workstation\scripts_recovery_test"
$LOGS     = $env:LEXMIND_LOG_DIR
$MANIFEST = $env:LEXMIND_MANIFEST_DIR

Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  LexMind-Omni V6.1  一鍵沙盒驗證啟動      " -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: 清除所有殘留進程
Write-Host "[1/5] 清除殘留進程..." -ForegroundColor Yellow
try { taskkill /F /IM python.exe  /T 2>&1 | Out-Null } catch {}
try { taskkill /F /IM pythonw.exe /T 2>&1 | Out-Null } catch {}
try { taskkill /F /IM node.exe    /T 2>&1 | Out-Null } catch {}
try { taskkill /F /IM ffmpeg.exe  /T 2>&1 | Out-Null } catch {}
Write-Host "  [OK] 進程清除完畢" -ForegroundColor Green
Start-Sleep -Seconds 2

# Step 2: 建立目錄 & 重置鎖定與金鑰
Write-Host "[2/5] 重置鎖定與金鑰狀態..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $LOGS     | Out-Null
New-Item -ItemType Directory -Force -Path $MANIFEST | Out-Null
Remove-Item "$MANIFEST\workflow.lock" -Force -ErrorAction SilentlyContinue
'{"exhausted_keys":[]}' | Out-File "C:\LocalAI_Workstation\config\quota_state.json" -Encoding UTF8 -NoNewline
Write-Host "  [OK] 鎖定與金鑰狀態已重置" -ForegroundColor Green

# Step 3: [Fix1] python.exe + Redirect 啟動主工作流
Write-Host "[3/5] 啟動主工作流引擎..." -ForegroundColor Yellow
$PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) { Write-Error "找不到 Python，請確認 PATH"; exit 1 }

$stdoutLog = Join-Path $LOGS "run_workflow_stdout.log"
$stderrLog = Join-Path $LOGS "run_workflow_stderr.log"
if (Test-Path $stdoutLog) { Remove-Item $stdoutLog -Force }
if (Test-Path $stderrLog) { Remove-Item $stderrLog -Force }

$proc = Start-Process $PythonExe `
    -ArgumentList "run_workflow.py" `
    -WorkingDirectory $ROOT `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError  $stderrLog `
    -WindowStyle Hidden -PassThru

Start-Sleep -Seconds 5
$aliveCheck = Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.Id)" -ErrorAction SilentlyContinue
if ($aliveCheck) {
    Write-Host "  [OK] run_workflow.py 存活 PID=$($proc.Id)" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] run_workflow.py 啟動後立即退出，請查看 stderr:" -ForegroundColor Red
    if (Test-Path $stderrLog) { Get-Content $stderrLog -Tail 20 -Encoding UTF8 }
    Read-Host "按 Enter 退出"
    exit 1
}

# Step 4: [Fix2] Streamlit -> web_dashboard.py
Write-Host "[4/5] 啟動網頁控制面板..." -ForegroundColor Yellow
$dashPath = Join-Path $ROOT "web_dashboard.py"
if (Test-Path $dashPath) {
    Start-Process powershell -WindowStyle Normal -ArgumentList @(
        "-NoProfile","-NoExit","-ExecutionPolicy","Bypass","-Command",
        "Clear-Host; Set-Location '$ROOT'; streamlit run web_dashboard.py --server.port 8506 --theme.base='light'"
    ) -WorkingDirectory $ROOT
    Start-Sleep -Seconds 5
    Start-Process "http://localhost:8506"
    Write-Host "  [OK] Streamlit -> http://localhost:8506" -ForegroundColor Green
} else {
    Write-Host "  [WARN] 找不到 web_dashboard.py" -ForegroundColor Yellow
}

# Step 5: 監控視窗
Write-Host "[5/5] 啟動監控視窗..." -ForegroundColor Yellow

Start-Process powershell -WindowStyle Normal -ArgumentList @(
    "-NoProfile","-NoExit","-ExecutionPolicy","Bypass","-File",
    "C:\LocalAI_Workstation\kpi_runner.ps1"
) -WorkingDirectory "C:\LocalAI_Workstation"
Write-Host "  [OK] KPI Monitor 已開啟" -ForegroundColor Green

Start-Process powershell -WindowStyle Normal -ArgumentList @(
    "-NoExit","-ExecutionPolicy","Bypass","-Command",
    "Clear-Host; Write-Host '沙盒工作流即時日誌' -ForegroundColor Yellow; Get-Content '$LOGS\workflow.log' -Encoding UTF8 -Wait -Tail 30"
) -WorkingDirectory $ROOT
Write-Host "  [OK] workflow.log 監控視窗已開啟" -ForegroundColor Green

Start-Process powershell -WindowStyle Normal -ArgumentList @(
    "-NoExit","-ExecutionPolicy","Bypass","-Command",
    "Clear-Host; Write-Host 'run_workflow stderr 監控' -ForegroundColor Red; Get-Content '$stderrLog' -Encoding UTF8 -Wait -Tail 30"
) -WorkingDirectory $ROOT
Write-Host "  [OK] stderr 監控視窗已開啟" -ForegroundColor Green

Write-Host ""
Write-Host "==============================================" -ForegroundColor Green
Write-Host "  全部完成！請觀察以下視窗:              " -ForegroundColor Green
Write-Host "  1. Streamlit  -> http://localhost:8506   " -ForegroundColor Green
Write-Host "  2. KPI Monitor (PowerShell 視窗)         " -ForegroundColor Green
Write-Host "  3. workflow.log 即時監控視窗             " -ForegroundColor Green
Write-Host "  4. stderr 監控視窗 (確認無 Python 錯誤)  " -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green
Write-Host ""
