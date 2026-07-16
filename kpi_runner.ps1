$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
Set-Location "C:\LocalAI_Workstation"

$INTERVAL = 300
$iteration = 0

Write-Host "=== LexMind KPI Monitor (5 min) ===" -ForegroundColor Magenta
Write-Host ""

while ($true) {
    $iteration++
    $ts = Get-Date -Format "HH:mm:ss"
    Write-Host "--- [$ts] KPI #$iteration ---" -ForegroundColor Cyan
    python scripts\kpi_monitor.py
    $next = (Get-Date).AddSeconds($INTERVAL).ToString("HH:mm:ss")
    Write-Host ""
    Write-Host "Next check: $next  (Ctrl+C to stop)" -ForegroundColor DarkGray
    Start-Sleep -Seconds $INTERVAL
}
