$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "=== LexMind Workflow Safe Restart ===" -ForegroundColor Cyan

$killed = 0
Get-WmiObject Win32_Process -Filter "Name='python.exe'" | ForEach-Object {
    $cmd = $_.CommandLine
    if ($cmd -match "run_workflow\.py") {
        Write-Host "  [KILL] run_workflow PID=$($_.ProcessId)" -ForegroundColor Red
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        $killed++
    } elseif ($cmd -match "progress_dashboard") {
        Write-Host "  [SKIP] dashboard PID=$($_.ProcessId)" -ForegroundColor Green
    } elseif ($cmd -match "watchdog") {
        Write-Host "  [SKIP] watchdog PID=$($_.ProcessId)" -ForegroundColor Green
    } elseif ($cmd -match "kpi_monitor") {
        Write-Host "  [SKIP] kpi_monitor PID=$($_.ProcessId)" -ForegroundColor Green
    }
}

if ($killed -eq 0) { Write-Host "  (no workflow process running)" -ForegroundColor Gray }
Start-Sleep -Seconds 2

Remove-Item "A:\manifests\workflow.lock" -Force -ErrorAction SilentlyContinue
'{"exhausted_keys":[]}' | Out-File "config\quota_state.json" -Encoding UTF8 -NoNewline

Start-Process python -ArgumentList "scripts\run_workflow.py" -WorkingDirectory "C:\LocalAI_Workstation" -WindowStyle Hidden
Write-Host "  [START] run_workflow.py restarted" -ForegroundColor Green

$wd = Get-WmiObject Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match "watchdog" }
if (-not $wd) {
    Start-Process python -ArgumentList "scripts\watchdog.py" -WorkingDirectory "C:\LocalAI_Workstation" -WindowStyle Hidden
    Write-Host "  [START] watchdog.py started" -ForegroundColor Green
}

Start-Sleep -Seconds 8
Write-Host ""
Get-Content "A:\logs\workflow.log" -Tail 5 -Encoding UTF8
