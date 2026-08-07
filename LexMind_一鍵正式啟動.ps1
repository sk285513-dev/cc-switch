$env:LEXMIND_ENV="v6_canary"
$env:LEXMIND_ENTERPRISE="1"
$env:PYTHONUTF8="1"
$env:PYTHONIOENCODING="utf-8"
$env:LEXMIND_MANIFEST_DIR="A:\manifests_v6"
$env:LEXMIND_LOG_DIR="A:\logs_v6"
[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
chcp 65001 | Out-Null
$ROOT="C:\LocalAI_Workstation"
$LOGS="A:\logs_v6"
$MANI="A:\manifests_v6"

Write-Host "[1/5] 清除殘留進程..." -ForegroundColor Yellow
Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe' OR Name='wscript.exe'" |
    Where-Object { $_.CommandLine -match "LexMind|LocalAI_Workstation|scripts_v6|app_v6" -and $_.CommandLine -notmatch "antigravity|gemini" -and $_.ProcessId -ne $PID } |
    ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } catch {} }

Get-CimInstance Win32_Process -Filter "Name LIKE 'powershell%.exe' OR Name LIKE 'pwsh%.exe'" |
    Where-Object { $_.CommandLine -match "progress_dashboard" -or $_.CommandLine -match "kpi_monitor" -or $_.CommandLine -match "watchdog" -or $_.CommandLine -match "logs_v6" } |
    ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } catch {} }
Write-Host "  [OK]" -ForegroundColor Green
Start-Sleep -Seconds 2

Write-Host "[2/5] 重置鎖定與狀態..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $LOGS | Out-Null
New-Item -ItemType Directory -Force -Path $MANI | Out-Null
if (-Not (Test-Path "$ROOT\config")) { New-Item -ItemType Directory -Force -Path "$ROOT\config" | Out-Null }
Remove-Item "$MANI\workflow.lock" -Force -ErrorAction SilentlyContinue
'{"exhausted_keys":[]}' | Out-File "$ROOT\config\quota_state.json" -Encoding ASCII -NoNewline
Write-Host "  [OK]" -ForegroundColor Green

Write-Host "[3/5] 啟動主工作流..." -ForegroundColor Yellow
if (Test-Path "$LOGS\run_workflow_stdout.log") { Remove-Item "$LOGS\run_workflow_stdout.log" -Force }
if (Test-Path "$LOGS\run_workflow_stderr.log") { Remove-Item "$LOGS\run_workflow_stderr.log" -Force }
Start-Process python -ArgumentList "scripts_v6\run_workflow.py" -RedirectStandardOutput "$LOGS\run_workflow_stdout.log" -RedirectStandardError "$LOGS\run_workflow_stderr.log" -WindowStyle Hidden -WorkingDirectory $ROOT -PassThru | Tee-Object -Variable proc | Out-Null
Start-Sleep -Seconds 6

$alive = Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.Id)" -ErrorAction SilentlyContinue
if ($alive) {
    Write-Host "  [OK] run_workflow.py PID=$($proc.Id)" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] 查看 stderr:" -ForegroundColor Red
    Get-Content "$LOGS\run_workflow_stderr.log" -Tail 30 -Encoding UTF8 -ErrorAction SilentlyContinue
    Read-Host "按 Enter 退出"
    exit 1
}

Write-Host "[4/5] 啟動 Streamlit..." -ForegroundColor Yellow
& "C:\Python312\pythonw.exe" "$ROOT\Launch_Isolated.py" powershell.exe -NoProfile -NoExit -ExecutionPolicy Bypass -Command "streamlit run app_v6.py --server.port 8506 --server.fileWatcherType none"
Start-Sleep -Seconds 3
Start-Process "http://localhost:8506"
Write-Host "  [OK] UI -> http://localhost:8506" -ForegroundColor Green
Start-Sleep -Seconds 5

Write-Host "[5/5] 啟動監控視窗..." -ForegroundColor Yellow
& "C:\Python312\pythonw.exe" "$ROOT\Launch_Isolated.py" powershell.exe -NoProfile -NoExit -ExecutionPolicy Bypass -File "$ROOT\kpi_runner.ps1"
& "C:\Python312\pythonw.exe" "$ROOT\Launch_Isolated.py" powershell.exe -NoExit -ExecutionPolicy Bypass -Command "Get-Content '$LOGS\workflow.log' -Encoding UTF8 -Wait -Tail 30"
& "C:\Python312\pythonw.exe" "$ROOT\Launch_Isolated.py" powershell.exe -NoExit -ExecutionPolicy Bypass -Command "Get-Content '$LOGS\run_workflow_stderr.log' -Encoding UTF8 -Wait -Tail 30"
& "C:\Python312\pythonw.exe" "$ROOT\Launch_Isolated.py" powershell.exe -NoProfile -NoExit -ExecutionPolicy Bypass -Command "`$env:PYTHONUTF8='1'; `$env:PYTHONIOENCODING='utf-8'; while (`$true) { try { python scripts_v6\progress_dashboard.py } catch {}; Write-Host '[自動重啟中...]' -ForegroundColor Yellow; Start-Sleep -Seconds 5 }"

Write-Host "  [OK] 4 個監控視窗已開啟" -ForegroundColor Green
Write-Host "Done! Streamlit -> http://localhost:8506" -ForegroundColor Green

