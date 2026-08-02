$ErrorActionPreference = "Stop"
$WorkspacePath = "C:\LocalAI_Workstation"
$ScriptPath = Join-Path $WorkspacePath "scripts_v6\watchdog_monitor.py"

Write-Host "LexMind V6 Launcher starting..."

$PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) {
    Write-Error "Python not found in PATH"
    exit 1
}
Write-Host "Using Python: $PythonExe"

$env:LEXMIND_ENV = "v6_canary"
$env:LEXMIND_PORT = "8086"
$env:LEXMIND_MANIFEST_DIR = "A:\manifests_v6"

$envList = @(
    "LEXMIND_ENV=v6_canary",
    "LEXMIND_PORT=8086",
    "LEXMIND_MANIFEST_DIR=A:\manifests_v6"
)

Write-Host "Injected env vars: LEXMIND_ENV=v6_canary, LEXMIND_PORT=8086"
Write-Host "Starting watchdog_monitor.py in background..."

$wmi_class = [wmiclass]"root\cimv2:Win32_Process"
$wmi_inParams = $wmi_class.GetMethodParameters("Create")
$wmi_inParams.CommandLine = "`"$PythonExe`" `"$ScriptPath`""
$wmi_inParams.CurrentDirectory = $WorkspacePath

$startup = ([wmiclass]"root\cimv2:Win32_ProcessStartup").CreateInstance()
$startup.EnvironmentVariables = $envList
$wmi_inParams.ProcessStartupInformation = $startup

$wmi_outParams = $wmi_class.InvokeMethod("Create", $wmi_inParams, $null)

if ($wmi_outParams.ReturnValue -eq 0) {
    $pid_v6 = $wmi_outParams.ProcessId
    Write-Host "WMI reported success (PID: $pid_v6), verifying in 3 seconds..." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
    $stillAlive = Get-CimInstance Win32_Process -Filter "ProcessId=$pid_v6" -ErrorAction SilentlyContinue
    if ($stillAlive) {
        Write-Host "SUCCESS: watchdog_monitor.py is running (PID: $pid_v6)" -ForegroundColor Green
    } else {
        Write-Host "FAILED: process exited immediately, check A:\logs_v6\watchdog.log" -ForegroundColor Red
    }
} else {
    Write-Host "FAILED: WMI Create error code: $($wmi_outParams.ReturnValue)" -ForegroundColor Red
}
