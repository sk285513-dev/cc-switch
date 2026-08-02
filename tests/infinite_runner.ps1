$ErrorActionPreference = "Stop"
$LogFile = "C:\LocalAI_Workstation\logs\infinite_runner.log"
$LogDir = Split-Path $LogFile
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
}
$Env:PYTHONIOENCODING = "utf-8"

Write-Output "[$(Get-Date -Format 's')] 啟動無限耐久壓力測試 (Soak Testing)..." | Out-File -Append -Encoding UTF8 -FilePath $LogFile

while ($true) {
    Write-Output "[$(Get-Date -Format 's')] 開始執行新的一輪測試..." | Out-File -Append -Encoding UTF8 -FilePath $LogFile
    
    # 執行 AppTest 邏輯腳本
    python C:\LocalAI_Workstation\tests\system_ui_tester.py
    
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        Write-Output "[$(Get-Date -Format 's')] ⚠️ 測試迴圈偵測到異常退出，代碼: $exitCode" | Out-File -Append -Encoding UTF8 -FilePath $LogFile
    } else {
        Write-Output "[$(Get-Date -Format 's')] ✅ 本輪測試順利完成" | Out-File -Append -Encoding UTF8 -FilePath $LogFile
    }
    
    # 休息 5 秒後繼續下一輪
    Start-Sleep -Seconds 5
}
