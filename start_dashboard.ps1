# 啟動 Streamlit 儀表板
Write-Host "[啟動] 正在背景啟動 Streamlit Dashboard..." -ForegroundColor Cyan

# 確認 app.py 存在
if (Test-Path "C:\LocalAI_Workstation\scripts_v6\app.py") {
    Start-Process powershell -ArgumentList "-NoExit -Command `"cd C:\LocalAI_Workstation\scripts_v6; streamlit run app.py`""
    Write-Host "[OK] Dashboard 已開啟新視窗，請查看。預設位址: http://localhost:8501" -ForegroundColor Green
} else {
    Write-Host "[ERROR] 找不到 app.py" -ForegroundColor Red
}
