import os

wizard_content = '''# 啟動設定精靈.ps1
# 設定主控台編碼為 UTF-8 確保中文顯示正常
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "正在啟動 LexMind 互動式設定與資安守護精靈..." -ForegroundColor Cyan
Write-Host "請稍候..." -ForegroundColor DarkGray

# 切換到腳本目錄
Set-Location -Path "C:\LocalAI_Workstation"

# 使用 python 執行精靈
python .\scripts\setup_wizard.py

Write-Host "
程式已結束。" -ForegroundColor Green
Read-Host "按下 Enter 鍵關閉視窗"
'''

ultimate_content = '''$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "=== LexMind-Omni 終極一鍵重啟與監控啟動程序 ===" -ForegroundColor Cyan
Write-Host "1. 正在強制清理舊的卡死進程..." -ForegroundColor Yellow

$killed = 0
Get-WmiObject Win32_Process -Filter "Name='python.exe'" | ForEach-Object {
    $cmd = $_.CommandLine
    if ($cmd -match "run_workflow\.py" -or $cmd -match "watchdog" -or $cmd -match "progress_dashboard" -or $cmd -match "streamlit" -or $cmd -match "kpi_monitor") {
        Write-Host "  [KILL] PID=$($_.ProcessId) ($cmd)" -ForegroundColor Red
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        $killed++
    }
}
if ($killed -eq 0) { Write-Host "  (沒有發現殘留進程)" -ForegroundColor Gray }
Start-Sleep -Seconds 2

Write-Host "2. 正在解除鎖定與重置狀態..." -ForegroundColor Yellow
Remove-Item "A:\manifests\workflow.lock" -Force -ErrorAction SilentlyContinue
'{"exhausted_keys":[]}' | Out-File "config\quota_state.json" -Encoding UTF8 -NoNewline

Write-Host "3. 正在背景重啟轉譯引擎 (自動套用 Vertex AI 與短秒數放行)..." -ForegroundColor Yellow
Start-Process python -ArgumentList "scripts\run_workflow.py" -WorkingDirectory "C:\LocalAI_Workstation" -WindowStyle Hidden
Start-Process python -ArgumentList "scripts\watchdog.py" -WorkingDirectory "C:\LocalAI_Workstation" -WindowStyle Hidden
Write-Host "  ✅ 背景引擎啟動成功！" -ForegroundColor Green

Write-Host "4. 正在開啟 Streamlit 網頁介面..." -ForegroundColor Yellow
Start-Process powershell -WindowStyle Normal -ArgumentList "-NoExit","-ExecutionPolicy","Bypass","-Command","python -m streamlit run app.py" -WorkingDirectory "C:\LocalAI_Workstation"
Start-Sleep -Seconds 3
Write-Host "  ✅ Streamlit 介面已觸發！" -ForegroundColor Green

Write-Host "5. 正在彈出三大監督視窗 (包含全新的 SRE 智慧哨兵)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit","-Command","python scripts\sre_watchdog.py" -WorkingDirectory "C:\LocalAI_Workstation"
Start-Process powershell -ArgumentList "-NoExit","-ExecutionPolicy","Bypass","-File","C:\LocalAI_Workstation\kpi_runner.ps1" -WorkingDirectory "C:\LocalAI_Workstation"
Start-Process powershell -ArgumentList "-NoExit","-Command","python 'scripts\progress_dashboard.py'" -WorkingDirectory "C:\LocalAI_Workstation"
Write-Host "  ✅ 三大監控視窗 (SRE, KPI, Dashboard) 已開啟！" -ForegroundColor Green

Write-Host ""
Write-Host "全部啟動完成！請觀察彈出的三個黑畫面與瀏覽器。您可以直接關閉此視窗。" -ForegroundColor Cyan
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
'''

with open(r"C:\LocalAI_Workstation\啟動設定精靈.ps1", "w", encoding="utf-8-sig") as f:
    f.write(wizard_content)

with open(r"C:\LocalAI_Workstation\LexMind一鍵啟動_終極版.ps1", "w", encoding="utf-8-sig") as f:
    f.write(ultimate_content)

print("RESTORED SUCCESSFULLY")
