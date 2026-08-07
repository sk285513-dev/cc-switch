$ROOT="C:\LocalAI_Workstation"
Start-Process wscript.exe -ArgumentList "`"$ROOT\dumpargs.vbs`" powershell.exe -NoProfile -NoExit -ExecutionPolicy Bypass -File `"$ROOT\kpi_runner.ps1`"" -Wait
Get-Content "C:\LocalAI_Workstation\wscript_args.txt"
