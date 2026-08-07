# ============================================================
#  LexMind-Omni  V6.1 沙盒隔離測試版 (Sandbox Test Launcher)
# ============================================================
$env:LEXMIND_ENV      = "v6_canary"
$env:LEXMIND_ENTERPRISE = "1"
$env:PYTHONUTF8       = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:LEXMIND_MANIFEST_DIR = "A:\manifests_v6"
$env:LEXMIND_LOG_DIR = "A:\logs_v6"
$env:LEXMIND_WORKDIR = "C:\LocalAI_Workstation\scripts_recovery_test"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

$ROOT = "C:\LocalAI_Workstation\scripts_recovery_test"
Set-Location $ROOT

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  LexMind-Omni 沙盒隔離測試啟動" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ── STEP 1: Kill stale processes ──────────────────────────────
Write-Host "[1/5] 清除干擾進程 (Killing stale processes)..." -ForegroundColor Yellow

try { taskkill /F /IM python.exe /T 2>&1 | Out-Null } catch {}
try { taskkill /F /IM pythonw.exe /T 2>&1 | Out-Null } catch {}
try { taskkill /F /IM node.exe /T 2>&1 | Out-Null } catch {}
try { taskkill /F /IM ffmpeg.exe /T 2>&1 | Out-Null } catch {}

Write-Host "  [OK] Python, Node, FFmpeg 進程已清除。" -ForegroundColor Green
Start-Sleep -Seconds 2

# ── STEP 2: Reset locks & quota ───────────────────────────────
Write-Host "[2/5] 重置鎖定與金鑰狀態..." -ForegroundColor Yellow

Remove-Item "$env:LEXMIND_MANIFEST_DIR\workflow.lock" -Force -ErrorAction SilentlyContinue
if (-not (Test-Path "C:\LocalAI_Workstation\config")) { New-Item -ItemType Directory -Path "C:\LocalAI_Workstation\config" -Force | Out-Null }
'{"exhausted_keys":[]}' | Out-File "C:\LocalAI_Workstation\config\quota_state.json" -Encoding UTF8 -NoNewline
if (-not (Test-Path "A:\logs_v6")) { New-Item -ItemType Directory -Path "A:\logs_v6" -Force | Out-Null }

Write-Host "  [OK] 鎖定與狀態已重置。" -ForegroundColor Green

# ── STEP 3: Background engines ────────────────────────────────
Write-Host "[3/5] 啟動背景引擎 (使用 python.exe 避免 10106)..." -ForegroundColor Yellow

$PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) {
    Write-Error "找不到 Python，請確認已加入 PATH"
    exit 1
}

$stdoutLog = Join-Path $env:LEXMIND_LOG_DIR "run_workflow_stdout.log"
$stderrLog = Join-Path $env:LEXMIND_LOG_DIR "run_workflow_stderr.log"

$proc = Start-Process $PythonExe `
    -ArgumentList "run_workflow.py" `
    -WorkingDirectory $ROOT `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog `
    -WindowStyle Hidden `
    -PassThru

Write-Host "  [OK] 主工作流已啟動 (PID: $($proc.Id))" -ForegroundColor Green

# (暫時只啟動主流程，為了觀察 Vertex AI 打通狀態)

# ── STEP 4: Streamlit UI ──────────────────────────────────────
Write-Host "[4/5] 啟動網頁儀表板 (Streamlit)..." -ForegroundColor Yellow

if (Test-Path "web_dashboard.py") {
    Start-Process powershell `
        -WindowStyle Normal `
        -ArgumentList @(
            "-NoProfile","-NoExit","-ExecutionPolicy","Bypass","-Command",
            "Clear-Host; Write-Host '=== 正在啟動網頁儀表板 ===' -ForegroundColor Cyan; Set-Location '$ROOT'; streamlit run web_dashboard.py --server.port 8506 --theme.base=`"light`""
        ) `
        -WorkingDirectory $ROOT
    Write-Host "  [OK] Streamlit 啟動中..." -ForegroundColor Green
} else {
    Write-Host "  [WARN] 找不到 web_dashboard.py，跳過啟動 UI。" -ForegroundColor Yellow
}

# ── STEP 5: Monitor windows ───────────────────────────────────
Write-Host "[5/5] 啟動監控視窗..." -ForegroundColor Yellow

# Workflow Log Tail
Start-Process powershell `
    -WindowStyle Normal `
    -ArgumentList @(
        "-NoExit","-ExecutionPolicy","Bypass","-Command",
        "Clear-Host; Write-Host '=== 正在即時監控沙盒工作流進度 (workflow_v6.log) ===' -ForegroundColor Yellow; Get-Content ""$env:LEXMIND_LOG_DIR\workflow.log"" -Encoding UTF8 -Wait -Tail 30"
    ) `
    -WorkingDirectory $ROOT

Write-Host ""
Write-Host "沙盒測試環境啟動完成！" -ForegroundColor Green
Write-Host "請觀察 PowerShell 監控視窗的 Vertex AI 呼叫日誌。" -ForegroundColor Green
Start-Sleep -Seconds 3
