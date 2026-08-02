Set WshShell = CreateObject("WScript.Shell")
' [機制一：實體會話突破機制 (Session 0 Breakthrough)] - 設置 CRAWLER_HEADFUL=1 環境變數，讓爬蟲以 headful 模式顯示在實體桌面
' 透過 SetEnvironmentVariable 在當前進程繼承給子進程 (Python)
WshShell.Environment("Process")("CRAWLER_HEADFUL") = "1"
' SW_SHOWNORMAL=1, False=非同步脫離父進程
WshShell.Run "python C:\LocalAI_Workstation\bot_ultimate_real_crawler.py", 1, False
