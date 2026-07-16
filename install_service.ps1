# LexMind-Omni 永久服務安裝腳本
# 需要以系統管理員身份執行
# 用法：powershell -ExecutionPolicy Bypass -File install_service.ps1

$BASE = "C:\LocalAI_Workstation"
$PYTHON = (Get-Command python).Source
$WATCHDOG = "$BASE\scripts\watchdog.py"
$TASK_NAME = "LexMind-Omni-Watchdog"

Write-Host "==================================================="
Write-Host " LexMind-Omni Watchdog 永久服務安裝程式"
Write-Host "==================================================="
Write-Host "Python: $PYTHON"
Write-Host "Watchdog: $WATCHDOG"
Write-Host ""

# 刪除舊任務（如存在）
schtasks /Delete /TN $TASK_NAME /F 2>$null | Out-Null

# 建立新排程任務
$ACTION_CMD = "`"$PYTHON`" `"$WATCHDOG`""
$XML = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>LexMind-Omni 法律實務AI工作站 — 永久守護程式（開機自啟、崩潰重啟）</Description>
  </RegistrationInfo>
  <Triggers>
    <BootTrigger>
      <Enabled>true</Enabled>
      <Delay>PT30S</Delay>
    </BootTrigger>
    <LogonTrigger>
      <Enabled>true</Enabled>
      <Delay>PT10S</Delay>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>false</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
    <RestartOnFailure>
      <Interval>PT1M</Interval>
      <Count>999</Count>
    </RestartOnFailure>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>$PYTHON</Command>
      <Arguments>"$WATCHDOG"</Arguments>
      <WorkingDirectory>$BASE</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"@

$XML_FILE = "$env:TEMP\lexmind_task.xml"
$XML | Out-File -FilePath $XML_FILE -Encoding Unicode
schtasks /Create /TN $TASK_NAME /XML $XML_FILE /F
Remove-Item $XML_FILE -ErrorAction SilentlyContinue

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "[OK] 工作排程任務 '$TASK_NAME' 已成功安裝！" -ForegroundColor Green
    Write-Host "     - 開機 30 秒後自動啟動"
    Write-Host "     - 崩潰後 1 分鐘內自動重啟（最多 999 次）"
    Write-Host "     - 登入時自動啟動"
    Write-Host ""
    Write-Host "立刻啟動 watchdog..."
    schtasks /Run /TN $TASK_NAME
    Write-Host "[OK] Watchdog 已啟動。" -ForegroundColor Green
} else {
    Write-Host "[ERROR] 安裝失敗，請確認以系統管理員身份執行此腳本。" -ForegroundColor Red
}

Write-Host ""
Write-Host "查看任務狀態："
Write-Host "  schtasks /Query /TN $TASK_NAME /V /FO LIST"
Write-Host ""
Write-Host "手動停止："
Write-Host "  schtasks /End /TN $TASK_NAME"
Write-Host ""
