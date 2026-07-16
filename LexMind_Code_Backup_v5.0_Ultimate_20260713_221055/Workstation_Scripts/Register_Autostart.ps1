# ══════════════════════════════════════════════════════════════
# 將 LexMind-Omni 啟動腳本註冊到 Windows 工作排程器
# 以系統管理員身份執行此腳本一次即可
# 儲存於: C:\LocalAI_Workstation\Register_Autostart.ps1
# ══════════════════════════════════════════════════════════════

$STARTUP_SCRIPT = "C:\LocalAI_Workstation\LexMind_Startup.ps1"
$TASK_NAME      = "LexMind-Omni 自動啟動"

# ── 確認腳本存在 ──────────────────────────────────────────────
if (-not (Test-Path $STARTUP_SCRIPT)) {
    Write-Error "找不到啟動腳本: $STARTUP_SCRIPT"
    exit 1
}

# ── 移除舊任務（避免重複） ────────────────────────────────────
$existing = Get-ScheduledTask -TaskName $TASK_NAME -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "移除舊工作排程..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TASK_NAME -Confirm:$false
}

# ── 建立執行動作 ──────────────────────────────────────────────
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$STARTUP_SCRIPT`""

# ── 觸發條件：使用者登入時執行 ───────────────────────────────
$trigger = New-ScheduledTaskTrigger -AtLogOn

# ── 主體設定：以目前使用者身份執行，擁有最高權限 ─────────────
$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Highest

# ── 設定：失敗時重試 3 次，每次間隔 1 分鐘 ───────────────────
$settings = New-ScheduledTaskSettingsSet `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable

# ── 延遲 30 秒後執行（等待桌面環境就緒） ─────────────────────
$trigger.Delay = "PT30S"

# ── 註冊工作排程 ──────────────────────────────────────────────
Register-ScheduledTask `
    -TaskName  $TASK_NAME `
    -Action    $action `
    -Trigger   $trigger `
    -Principal $principal `
    -Settings  $settings `
    -Force

Write-Host ""
Write-Host "✅ 工作排程器任務已成功建立！" -ForegroundColor Green
Write-Host "   任務名稱: $TASK_NAME" -ForegroundColor Cyan
Write-Host "   觸發條件: 使用者登入後 30 秒" -ForegroundColor Cyan
Write-Host "   執行腳本: $STARTUP_SCRIPT" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 驗證方式: 開啟 [工作排程器] → 搜尋 '$TASK_NAME'" -ForegroundColor Yellow
