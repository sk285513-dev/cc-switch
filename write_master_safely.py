import codecs

script_content = """# ══ LexMind-Omni 一鍵啟動 ══
$env:PYTHONUTF8="1"; $env:PYTHONIOENCODING="utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Remove-Item "A:\\manifests\\workflow.lock" -Force -ErrorAction SilentlyContinue
'{"exhausted_keys":[]}' | Out-File "C:\\LocalAI_Workstation\\config\\quota_state.json" -Encoding UTF8 -NoNewline

# Dashboard
Start-Process powershell -WindowStyle Normal -ArgumentList "-NoExit","-ExecutionPolicy","Bypass","-File","C:\\LocalAI_Workstation\\dashboard_runner.ps1"

# KPI Runner
Start-Process powershell -WindowStyle Normal -ArgumentList "-NoExit","-ExecutionPolicy","Bypass","-File","C:\\LocalAI_Workstation\\kpi_runner.ps1"

# Watchdog (Hidden)
$w = Get-WmiObject Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match "watchdog\\.py" }
if (-not $w) { 
    Start-Process "C:\\Python312\\python.exe" -WindowStyle Hidden -ArgumentList "scripts\\watchdog.py" -WorkingDirectory "C:\\LocalAI_Workstation"
    Write-Host "Watchdog started" -ForegroundColor Green 
} else { 
    Write-Host "Watchdog already running PID=$($w.ProcessId)" -ForegroundColor Green 
}

# UI Server
$n = Get-WmiObject Win32_Process -Filter "Name='node.exe'" | Where-Object { $_.CommandLine -match "server" }
if (-not $n) { 
    Start-Process powershell -WindowStyle Normal -ArgumentList "-NoExit","-ExecutionPolicy","Bypass","-Command","npm run dev" -WorkingDirectory "C:\\Users\\temp\\antigravity\\LexMind-Omni-法律實務-AI-工作站"
} else { 
    Write-Host "UI already running" -ForegroundColor Green 
}
"""

with codecs.open(r"C:\LocalAI_Workstation\Master_Startup.ps1", "w", "utf-8-sig") as f:
    f.write(script_content)
