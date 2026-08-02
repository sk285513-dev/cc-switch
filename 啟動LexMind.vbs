Set WshShell = CreateObject("WScript.Shell")
' 以 -ExecutionPolicy Bypass 強制啟動 PS1，繞過 RemoteSigned Zone 封鎖
WshShell.Run "powershell -NoProfile -ExecutionPolicy Bypass -File ""C:\LocalAI_Workstation\LexMind一鍵啟動_終極版.ps1""", 1, False
