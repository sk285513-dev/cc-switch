$repoUrl = "https://github.com/sk285513-dev/cc-switch.git"
$branch = "sk285513-dev"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$commitMsg = "系統自動備份: $timestamp"

Write-Host "開始執行自動備份至 GitHub..." -ForegroundColor Cyan

if (-not (Test-Path ".git")) {
    git init
    git remote add origin $repoUrl
    git branch -M $branch
}

git add .
git commit -m "$commitMsg"
git push -u origin $branch --force

Write-Host "備份完成！" -ForegroundColor Green
