$env:PYTHONUTF8       = "1"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

$ROOT = "C:\LocalAI_Workstation"
Set-Location $ROOT

Write-Host "=== 正在啟動 LexMind-Omni 企業級網頁控制面板 (Streamlit) ===" -ForegroundColor Cyan
Write-Host "請保持此 PowerShell 視窗開啟。若要關閉伺服器，請按 Ctrl+C。" -ForegroundColor Yellow

# 啟動 Streamlit
streamlit run app.py --theme.base="light"
