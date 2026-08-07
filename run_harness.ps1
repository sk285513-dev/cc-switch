Write-Host "Running comprehensive tool testing harness..."
cd C:\LocalAI_Workstation

Write-Host "1. Running Shutdown Script to ensure clean state..."
powershell -ExecutionPolicy Bypass -File .\LexMind_一鍵完全關閉系統.ps1

Write-Host "2. Running Startup Script..."
powershell -ExecutionPolicy Bypass -File .\LexMind_一鍵正式啟動.ps1

Write-Host "3. Starting Telemetry Daemon..."
Start-Process python -ArgumentList "scripts_v6\auto_telemetry_debugger.py" -NoNewWindow -RedirectStandardOutput A:\logs_v6\telemetry_daemon.log

Write-Host "4. Starting Vision Daemon..."
Start-Process python -ArgumentList "scripts_v6\auto_vision_debugger.py" -NoNewWindow -RedirectStandardOutput A:\logs_v6\vision_daemon.log

Write-Host "Sleeping for 65 seconds to let first loop complete..."
Start-Sleep -Seconds 65

Write-Host "Reading Telemetry Daemon output..."
Get-Content A:\logs_v6\telemetry_daemon.log -Encoding UTF8

Write-Host "Reading Vision Daemon output..."
Get-Content A:\logs_v6\vision_daemon.log -Encoding UTF8

Write-Host "Reading Master Report..."
Get-Content A:\logs_v6\master_debug_report.txt -Encoding UTF8 -ErrorAction SilentlyContinue

Write-Host "Test complete. Shutting down again..."
powershell -ExecutionPolicy Bypass -File .\LexMind_一鍵完全關閉系統.ps1
