$TaskName = "LexMind_Interactive_Crawler"
$Action = "python C:\LocalAI_Workstation\bot_ultimate_real_crawler.py"

Write-Host "Creating interactive task for Session 1 breakthrough..."

# Create interactive task (/IT represents Interactive, showing on current logged-in user screen)
schtasks /create /tn $TaskName /tr $Action /sc once /st 00:00 /it /f /ru $env:USERNAME

Write-Host "Triggering execution..."
# Trigger immediately
schtasks /run /tn $TaskName

Start-Sleep -Seconds 3

Write-Host "Cleaning up task scheduler trace..."
schtasks /delete /tn $TaskName /f

Write-Host "Task projected. Please check physical desktop."
