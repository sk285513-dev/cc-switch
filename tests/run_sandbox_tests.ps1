$ErrorActionPreference = "Stop"

$Action = "cmd /c python C:\LocalAI_Workstation\tests\sandbox_15_mechanisms.py > C:\LocalAI_Workstation\tests\sandbox_run.log 2>&1"
$TaskName = "LexMind_Interactive_Crawler_Test"

for ($i = 1; $i -le 3; $i++) {
    Write-Host "`n========== Run $i =========="
    
    # Mechanism 1: Session 0 Breakthrough
    Write-Host "[Mechanism 1] Create Interactive Task Scheduler task..."
    schtasks /create /tn $TaskName /tr $Action /sc once /st 00:00 /it /f /ru $env:USERNAME
    
    Write-Host "[Mechanism 1] Run task..."
    schtasks /run /tn $TaskName
    
    Write-Host "Waiting for script to finish (about 20 seconds)..."
    Start-Sleep -Seconds 20
    
    if (Test-Path "C:\LocalAI_Workstation\tests\sandbox_run.log") {
        Get-Content "C:\LocalAI_Workstation\tests\sandbox_run.log"
    } else {
        Write-Host "No log file found! Script might have failed to start."
    }
    
    Write-Host "[Mechanism 1] Delete task..."
    schtasks /delete /tn $TaskName /f
}

Write-Host "`n========== 3 Runs Completed =========="
