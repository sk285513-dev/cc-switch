Write-Host "Running workflow trigger test..."
Start-Process python -ArgumentList "scripts_v6\run_workflow.py" -WindowStyle Hidden -WorkingDirectory "C:\LocalAI_Workstation" -PassThru | Tee-Object -Variable proc | Out-Null
Start-Sleep -Seconds 10
Write-Host "Triggering Telemetry Debugger..."
python scripts_v6\auto_telemetry_debugger.py
Write-Host "Triggering Vision Debugger..."
python scripts_v6\auto_vision_debugger.py
Write-Host "Reading Telemetry Report..."
Get-Content -Path "A:\logs_v6\master_debug_report.txt" -Encoding UTF8
