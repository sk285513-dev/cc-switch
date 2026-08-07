Set WshShell = CreateObject("WScript.Shell")
cmd = "powershell.exe -NoProfile -NoExit -ExecutionPolicy Bypass -File C:\LocalAI_Workstation\kpi_runner.ps1 "
WshShell.Run cmd, 1, False
