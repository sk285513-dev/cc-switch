# 強制設定 Python 輸出編碼為 UTF-8，防止表情符號導致的 UnicodeEncodeError
$env:PYTHONIOENCODING = 'utf-8'

$workDir = 'C:\LocalAI_Workstation'
$agentPath = 'C:\LocalAI_Workstation\scripts\agent_core.py'
$ingestPath = 'C:\LocalAI_Workstation\scripts\ingest_law.py'
$dbPath = 'C:\LocalAI_Workstation\RAGFlow_Datasets'

Write-Host '
🌟 [Auto-Pilot v2] 啟動強效自癒模式...' -ForegroundColor Magenta
$success = $false
$retryCount = 0
$maxRetries = 20

while (-not $success -and $retryCount -lt $maxRetries) {
    $retryCount++
    Write-Host '
🔄 [嘗試 $retryCount] 啟動 Agent...' -ForegroundColor Gray
    
    # 執行 Agent 並捕捉輸出
    $output = python $agentPath 2>&1 | Out-String
    Write-Host $output

    # --- 錯誤模式匹配與自動校正 ---

    # 模式 1: 維度不匹配
    if ($output -match 'dimension of 768, got 384') {
        Write-Host '🚨 偵測到 [維度不匹配] $\rightarrow$ 正在強制清除鎖定文件並重新 Ingest...' -ForegroundColor Yellow
        
        # 【核心修正】先殺死所有 python 進程，釋放 ChromaDB 文件鎖
        Stop-Process -Name 'python' -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2 # 給系統一點時間釋放文件
        
        Remove-Item -Recurse -Force $dbPath -ErrorAction SilentlyContinue
        python $ingestPath
        continue 
    }

    # 模式 2: 知識庫為空
    if ($output -match '知識庫目前為空') {
        Write-Host '🚨 偵測到 [知識庫缺失] $\rightarrow$ 自動執行 Ingest...' -ForegroundColor Yellow
        python $ingestPath
        continue
    }

    # 模式 3: 記憶體不足/伺服器錯誤
    if ($output -match '500 Server Error' -or $output -match 'out-of-memory') {
        Write-Host '🚨 偵測到 [OOM/500 錯誤] $\rightarrow$ 重新 Pull 模型...' -ForegroundColor Yellow
        ollama pull deepseek-r1:7b
        continue
    }

    # 模式 4: 編碼/語法錯誤
    if ($output -match 'SyntaxError' -or $output -match 'Non-UTF-8' -or $output -match 'UnicodeEncodeError') {
        Write-Host '🚨 偵測到 [編碼/語法錯誤] $\rightarrow$ 修復 UTF-8...' -ForegroundColor Yellow
        $files = Get-ChildItem -Path $workDir -Recurse -Include *.py, *.env, *.json
        foreach ($file in $files) {
            $content = Get-Content $file.FullName -Raw
            [System.IO.File]::WriteAllText($file.FullName, $content, [System.Text.Encoding]::UTF8)
        }
        continue
    }

    # 檢查成功標誌
    if ($output -match '✅ \[FINAL\] 流程成功完成') {
        Write-Host '
✨ [MISSION ACCOMPLISHED] Agent 已成功運行！' -ForegroundColor Green
        $success = $true
    }
}