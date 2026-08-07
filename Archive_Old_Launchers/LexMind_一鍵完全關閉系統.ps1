$callerPID = $PID
$scriptBlock = {
    param($OriginalPID)
    Write-Host "LexMind Stop Script (Elevated)"
    Write-Host "Killing targeted Python, Node, FFmpeg, and Wscript processes to ensure a clean slate..."
    
    $targets = Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe' OR Name='wscript.exe' OR Name='node.exe' OR Name='ffmpeg.exe'"
    foreach ($t in $targets) {
        if ($t.CommandLine -match "LexMind|LocalAI_Workstation|scripts_v6|app_v6") {
            try { Stop-Process -Id $t.ProcessId -Force -ErrorAction SilentlyContinue } catch {}
        }
    }

    Write-Host "Closing LexMind Terminal Windows..."
    $processes = Get-CimInstance Win32_Process -Filter "Name='powershell.exe' OR Name='pwsh.exe'"
    foreach ($p in $processes) {
        if ($p.CommandLine -match 'LocalAI_Workstation|scripts_v6|logs_v6|app_v6' -and $p.ProcessId -ne $PID -and $p.ProcessId -ne $OriginalPID) {
            try { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue } catch {}
        }
    }
    
    Write-Host "Releasing resource locks..."
    Remove-Item "A:\manifests_v6\workflow.lock" -Force -ErrorAction SilentlyContinue

    Write-Host "`nSuccessfully cleared all background processes, locks, and windows."
    Write-Host "Done. System completely shut down."
    Start-Sleep -Seconds 2
}

& $scriptBlock $callerPID
