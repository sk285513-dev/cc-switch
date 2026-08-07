Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "powershell.exe -NoProfile -NoExit -ExecutionPolicy Bypass -File C:\LocalAI_Workstation\kpi_runner.ps1 ", 1, False
