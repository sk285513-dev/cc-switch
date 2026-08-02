# 自動備份腳本 (git_sync.ps1)
# 此腳本會將 C:\LocalAI_Workstation\scripts 下的變更提交並推播至 GitHub

# 強制將工作目錄切換到腳本所在資料夾
Set-Location "C:\LocalAI_Workstation\scripts"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "開始進行 Git 自動同步與備份" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. 先嘗試拉取遠端最新的程式碼 (避免衝突)
Write-Host "正在檢查並拉取 GitHub 上的最新變更 (git pull)..." -ForegroundColor Yellow
git pull

# 2. 將所有修改加入暫存區
Write-Host "正在將本地端所有修改加入追蹤 (git add .)..." -ForegroundColor Yellow
git add .

# 3. 取得當前時間作為 Commit 訊息
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$commitMessage = "系統自動備份: $timestamp"

# 4. 提交變更
Write-Host "正在提交變更: $commitMessage" -ForegroundColor Yellow
git commit -m $commitMessage

# 5. 推播至 GitHub
Write-Host "正在推播至 GitHub (git push)..." -ForegroundColor Yellow
git push

Write-Host "========================================" -ForegroundColor Green
Write-Host "✅ 同步完成！您的程式碼已安全備份至 GitHub。" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
