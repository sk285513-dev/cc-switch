$WScriptShell = New-Object -ComObject WScript.Shell
$ShortcutPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\LexMindWatcher.lnk"
$Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "cmd.exe"
$Shortcut.Arguments = "/c start /min python C:\LocalAI_Workstation\src\long_media_pipeline\file_watcher.py"
$Shortcut.WorkingDirectory = "C:\LocalAI_Workstation\src\long_media_pipeline"
$Shortcut.WindowStyle = 7
$Shortcut.Save()

Write-Host "--------------------------------------------------------"
Write-Host "LexMind File Watcher Auto-Start configured successfully!"
Write-Host "Shortcut created at: $ShortcutPath"
Write-Host "The background service will automatically run at boot."
Write-Host "--------------------------------------------------------"
