# LexMind Reboot Watcher v3.0
# All strings are ASCII-only to avoid PS5.1 encoding issues

$LOG = "A:\logs\reboot_watcher.log"
New-Item -ItemType Directory -Force -Path "A:\logs" | Out-Null

function Write-Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "$ts $msg"
    $line | Add-Content -Path $LOG -Encoding UTF8
    Write-Host $line
}

function Test-SystemIdle {
    $wf = Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -match "run_workflow" }
    if ($wf) { return $false, "Workflow running (PID: $($wf.ProcessId -join ','))" }

    try {
        $ps = Invoke-RestMethod "http://127.0.0.1:11434/api/ps" -TimeoutSec 3
        if ($ps.models -and $ps.models.Count -gt 0) {
            return $false, "Ollama busy: $($ps.models.name -join ', ')"
        }
    } catch { }

    try {
        $maxTemp = (
            nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader |
            Where-Object { $_ -match "\d" } |
            ForEach-Object { [int]$_.Trim() } |
            Measure-Object -Maximum
        ).Maximum
        if ($maxTemp -ge 60) { return $false, "GPU too hot: ${maxTemp}C (need <60C)" }
    } catch { }

    return $true, "System idle - Workflow done, Ollama idle, GPU cool"
}

function Show-RebootDialog($statusMsg) {
    Add-Type -AssemblyName System.Windows.Forms
    $msg  = "LexMind Monitor: System is idle, safe to reboot!`n`n"
    $msg += "Status: $statusMsg`n`n"
    $msg += "After reboot, auto-start:`n"
    $msg += "  [1] Dashboard window`n"
    $msg += "  [2] KPI monitor window`n"
    $msg += "  [3] Workflow transcription window`n`n"
    $msg += "Reboot now?"
    return [System.Windows.Forms.MessageBox]::Show(
        $msg,
        "LexMind Reboot Suggestion",
        [System.Windows.Forms.MessageBoxButtons]::YesNo,
        [System.Windows.Forms.MessageBoxIcon]::Question
    )
}

# ---- main loop ----
Write-Log "=== LexMind Reboot Watcher started (check every 2 min) ==="
Write-Log "=== Conditions: Workflow idle + Ollama idle + GPU<60C ==="
Write-Host "Keep this window open. Press Ctrl+C to stop." -ForegroundColor Cyan

$n = 0
while ($true) {
    $n++
    $idle, $status = Test-SystemIdle
    $flag = if ($idle) { "[IDLE]" } else { "[BUSY]" }
    Write-Log "#$n $flag $status"

    if ($idle) {
        Write-Log "==> All conditions met! Showing reboot dialog..."
        try { msg.exe * "LexMind: System idle - reboot suggested. Check the monitor window." } catch { }

        $answer = Show-RebootDialog $status

        if ($answer -eq [System.Windows.Forms.DialogResult]::Yes) {
            Write-Log "==> User confirmed reboot. Counting down 60s..."
            for ($i = 60; $i -gt 0; $i -= 10) {
                Write-Host "Rebooting in ${i}s... (close window to cancel)" -ForegroundColor Red
                Start-Sleep -Seconds 10
            }
            Write-Log "==> Executing shutdown /r /t 0"
            shutdown /r /t 0
            break
        } else {
            Write-Log "==> User declined. Will ask again in 10 min."
            Start-Sleep -Seconds 600
        }
    } else {
        Start-Sleep -Seconds 120
    }
}
