Set WshShell = CreateObject("WScript.Shell")
' 透過 VBS 啟動，完全脫離終端機 Pipe，完美避開 0x800700E8 (The pipe is being closed) 崩潰
' 並且直接指向真正的腳本位置，不受中文路徑亂碼影響
WshShell.Run "python ""C:\LocalAI_Workstation\bot_ultimate_real_crawler.py""", 1, False
