if (-Not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Requesting Administrator privileges to read background processes..."
    $scriptBlock = {
        Write-Host "LexMind Stop Script (Elevated)"
        Write-Host "Killing all Python, Node, and FFmpeg processes to ensure a clean slate..."
        
        try { taskkill /F /IM python.exe /T 2>&1 | Out-Null } catch {}
        try { taskkill /F /IM pythonw.exe /T 2>&1 | Out-Null } catch {}
        try { taskkill /F /IM node.exe /T 2>&1 | Out-Null } catch {}
        try { taskkill /F /IM ffmpeg.exe /T 2>&1 | Out-Null } catch {}

        Write-Host "Closing LexMind Terminal Windows..."
        $processes = Get-CimInstance Win32_Process -Filter "Name='powershell.exe' OR Name='pwsh.exe'"
        foreach ($p in $processes) {
            if ($p.CommandLine -match 'LocalAI_Workstation|scripts_v6' -and $p.ProcessId -ne $PID) {
                try { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue } catch {}
            }
        }

        Write-Host "`nSuccessfully cleared all background processes and windows."
        Write-Host "Done. System completely shut down."
        Start-Sleep -Seconds 2
    }
    $encoded = [Convert]::ToBase64String([System.Text.Encoding]::Unicode.GetBytes($scriptBlock.ToString()))
    Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -EncodedCommand $encoded" -Verb RunAs
    exit
}
