$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "LexMind 系統啟動金鑰安全匯入程式..." -ForegroundColor Cyan
python C:\Users\temp\antigravity\LexMind-Omni-法律實務-AI-工作站\scripts\cli_key_import.py
