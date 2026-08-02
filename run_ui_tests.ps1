# 啟動 UI 自動化測試爬蟲機器人 (Playwright)
# 請對此檔案按右鍵 -> 使用 PowerShell 執行

Set-Location -Path "C:\LocalAI_Workstation"
Write-Host "即將啟動 UI 自動化測試爬蟲機器人..." -ForegroundColor Cyan

# 啟動 Playwright 腳本
python C:\Users\temp\.gemini\antigravity\brain\8956499f-a5a9-462d-9e66-9c8ff5328398\system_ui_tester.py

Write-Host "測試完畢，請按任意鍵退出..." -ForegroundColor Yellow
$Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown') | Out-Null
