$ErrorActionPreference = "Stop"

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:LEXMIND_ENTERPRISE = "1"
$env:LEXMIND_ENV = "v6_canary"

# 1. 顶部补：
$env:LEXMIND_WORKDIR = "C:\LocalAI_Workstation"
$env:LEXMIND_MANIFEST_DIR = "A:\manifests_v6"
$env:LEXMIND_LOG_DIR = "A:\logs_v6"

# 2. 修改变量定义
$root = $env:LEXMIND_WORKDIR
$logsDir = $env:LEXMIND_LOG_DIR
$manifestsDir = $env:LEXMIND_MANIFEST_DIR

$stdoutLog = Join-Path $logsDir "run_workflow_stdout.log"
$stderrLog = Join-Path $logsDir "run_workflow_stderr.log"
$workflowLog = Join-Path $logsDir "workflow.log"
$lockFile = Join-Path $manifestsDir "workflow.lock"
$quotaState = Join-Path $root "config\quota_state.json"

# 3. 补齐目录创建
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null
New-Item -ItemType Directory -Force -Path $manifestsDir | Out-Null

Write-Host "=== LexMind Workflow Safe Restart ===" -ForegroundColor Cyan

function Get-PythonProcesses {
    Get-WmiObject Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'"
}

function Get-WorkflowProcess {
    Get-PythonProcesses | Where-Object { $_.CommandLine -match "scripts_v6\\run_workflow\.py" }
}

function Get-WatchdogProcess {
    Get-PythonProcesses | Where-Object { $_.CommandLine -match "scripts_v6\\watchdog_monitor\.py" -or $_.CommandLine -match "scripts_v6\\watchdog\.py" }
}

$killed = 0
Get-PythonProcesses | ForEach-Object {
    $cmd = $_.CommandLine
    if ($null -eq $cmd) { return }

    if ($cmd -match "scripts_v6\\run_workflow\.py") {
        Write-Host "  [KILL] run_workflow PID=$($_.ProcessId)" -ForegroundColor Red
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        $killed++
    }
    elseif ($cmd -match "progress_dashboard") {
        Write-Host "  [SKIP] dashboard PID=$($_.ProcessId)" -ForegroundColor Green
    }
    elseif ($cmd -match "watchdog") {
        Write-Host "  [SKIP] watchdog PID=$($_.ProcessId)" -ForegroundColor Green
    }
    elseif ($cmd -match "kpi_monitor") {
        Write-Host "  [SKIP] kpi_monitor PID=$($_.ProcessId)" -ForegroundColor Green
    }
}

if ($killed -eq 0) {
    Write-Host "  (no workflow process running)" -ForegroundColor Gray
}

Start-Sleep -Seconds 2

if (Test-Path $lockFile) {
    Copy-Item $lockFile "$lockFile.bak" -Force -ErrorAction SilentlyContinue
    Remove-Item $lockFile -Force -ErrorAction SilentlyContinue
    Write-Host "  [CLEAN] workflow.lock removed" -ForegroundColor Yellow
}

if (Test-Path $quotaState) {
    Copy-Item $quotaState "$quotaState.bak" -Force -ErrorAction SilentlyContinue
}
'{"exhausted_keys":[]}' | Out-File $quotaState -Encoding UTF8 -NoNewline
Write-Host "  [RESET] quota_state.json cleared" -ForegroundColor Yellow

if (Test-Path $stdoutLog) { Remove-Item $stdoutLog -Force -ErrorAction SilentlyContinue }
if (Test-Path $stderrLog) { Remove-Item $stderrLog -Force -ErrorAction SilentlyContinue }

# 5. Start-Process automatically inherits $env:* variables in PowerShell
$proc = Start-Process python `
    -ArgumentList "scripts_v6\run_workflow.py" `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog `
    -WorkingDirectory $root `
    -WindowStyle Hidden `
    -PassThru

Write-Host "  [START] run_workflow.py launched PID=$($proc.Id)" -ForegroundColor Green

Start-Sleep -Seconds 6

$wf = Get-WorkflowProcess
if (-not $wf) {
    Write-Host "  [FAIL] run_workflow.py did not stay alive after launch." -ForegroundColor Red

    if (Test-Path $stderrLog) {
        Write-Host "`n--- stderr tail ---" -ForegroundColor Yellow
        Get-Content $stderrLog -Tail 30 -Encoding UTF8
    }

    if (Test-Path $stdoutLog) {
        Write-Host "`n--- stdout tail ---" -ForegroundColor Yellow
        Get-Content $stdoutLog -Tail 30 -Encoding UTF8
    }

    throw "Workflow restart failed: run_workflow.py is not running."
}
else {
    $wf | ForEach-Object {
        Write-Host "  [OK] run_workflow alive PID=$($_.ProcessId)" -ForegroundColor Green
    }
}

# 4. 彻底删除主动拉起 watchdog 的逻辑，只保留检测与提示
$wd = Get-WatchdogProcess
if (-not $wd) {
    Write-Host "  [WARN] watchdog_monitor is NOT running. Please start it separately." -ForegroundColor Yellow
}
else {
    $wd | ForEach-Object {
        Write-Host "  [OK] watchdog already alive PID=$($_.ProcessId)" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "--- workflow.log tail ---" -ForegroundColor Cyan
if (Test-Path $workflowLog) {
    Get-Content $workflowLog -Tail 10 -Encoding UTF8
}
else {
    Write-Host "workflow.log not found" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "--- stderr tail ---" -ForegroundColor Cyan
if (Test-Path $stderrLog) {
    Get-Content $stderrLog -Tail 10 -Encoding UTF8
}
else {
    Write-Host "(stderr log empty or not found)" -ForegroundColor Gray
}
