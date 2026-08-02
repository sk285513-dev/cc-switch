<#
.SYNOPSIS
核准等待中的短課程 (20~60分鐘) 進入 AI 處理佇列。
#>

$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$manifestDir = "A:\manifests"
$pendingFiles = Get-ChildItem -Path $manifestDir -Filter "*.json" | Where-Object { $_.Name -match "^task_" }

$foundPending = $false

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  LexMind 補充課程 (20~60分鐘) 人工審核系統" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

foreach ($file in $pendingFiles) {
    try {
        $json = Get-Content $file.FullName -Raw | ConvertFrom-Json
        if ($json.status -eq "pending_approval") {
            $foundPending = $true
            Write-Host "發現需手動核准的課程：" -ForegroundColor Yellow
            Write-Host "▶ 來源檔案：$($json.source_path)"
            Write-Host "▶ 任務名稱：$($json.source_name)"
            
            $validResponse = $false
            while (-not $validResponse) {
                $response = Read-Host "是否批准此課程進入排程作業？ (Y=批准 / N=拒絕 / S=跳過)"
                if ($response -match "^[Yy]$") {
                    $json.status = "queued"
                    $json | ConvertTo-Json -Depth 10 | Set-Content $file.FullName -Encoding UTF8
                    Write-Host "[✅ 已批准] 任務狀態已更新為 queued！背景系統將自動開始處理。" -ForegroundColor Green
                    $validResponse = $true
                } elseif ($response -match "^[Nn]$") {
                    $json.status = "rejected"
                    $json | ConvertTo-Json -Depth 10 | Set-Content $file.FullName -Encoding UTF8
                    Write-Host "[❌ 已拒絕] 任務已標記為 rejected，從此忽略此檔。" -ForegroundColor Red
                    $validResponse = $true
                } elseif ($response -match "^[Ss]$") {
                    Write-Host "[⏭️ 已跳過] 保留 pending_approval 狀態，下次再問。" -ForegroundColor Gray
                    $validResponse = $true
                } else {
                    Write-Host "無效輸入，請輸入 Y, N 或 S。" -ForegroundColor Red
                }
            }
            Write-Host "------------------------------------------"
        }
    } catch {
        Write-Host "讀取 JSON 發生錯誤: $($file.Name)" -ForegroundColor Red
    }
}

if (-not $foundPending) {
    Write-Host "🎉 目前沒有需要人工審核的補充課程！" -ForegroundColor Green
}
Write-Host ""
Write-Host "審核結束，請按任意鍵離開..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
