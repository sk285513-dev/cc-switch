# 測試機器人全域修復計畫一鍵啟動抓蟲指令
# 此腳本會依序執行三支重要的驗收測試

Write-Host "開始執行 Config 模組沙盒測試..." -ForegroundColor Cyan
C:\Python312\python.exe tests\sandbox_test_config.py
if ($LASTEXITCODE -ne 0) { Write-Host "Config 測試失敗！" -ForegroundColor Red; exit $LASTEXITCODE }

Write-Host "`n開始執行 幽靈狀態自動復原 沙盒測試..." -ForegroundColor Cyan
C:\Python312\python.exe tests\sandbox_test_zombie_recovery.py
if ($LASTEXITCODE -ne 0) { Write-Host "幽靈狀態復原測試失敗！" -ForegroundColor Red; exit $LASTEXITCODE }

Write-Host "`n開始執行 UI 全域整合測試 (AppTest)..." -ForegroundColor Cyan
C:\Python312\python.exe tests\system_ui_tester.py
if ($LASTEXITCODE -ne 0) { Write-Host "UI 整合測試失敗！" -ForegroundColor Red; exit $LASTEXITCODE }

Write-Host "
🎉 所有測試皆已順利通過！系統環境安全且合規。" -ForegroundColor Green
