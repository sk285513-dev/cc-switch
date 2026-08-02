# [CRITICAL CROSS-FILE DEPENDENCY WARNING]
# Upstream: LexMind_V6_沙盒驗證版.ps1
# Downstream: scripts_v6/kpi_monitor.py
# Shared State: KPI Logs

# ==============================================================================
# [CRITICAL DEPENDENCY WARNING] Group 8: 系統啟動與本地工作站入口 (Startup & Entry)
# ------------------------------------------------------------------------------
# ⚠️ 系統最高入口點！絕對禁止 AI 擅自覆蓋、魔改或閹割這些啟動腳本。
# 修改前請務必參閱：PIPELINE_DEPENDENCIES.md
# ==============================================================================
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:LEXMIND_ENTERPRISE = "1"
Set-Location "C:\LocalAI_Workstation"

$INTERVAL = 300
$iteration = 0

Write-Host "=== LexMind KPI Monitor (5 min) ===" -ForegroundColor Magenta
Write-Host ""

while ($true) {
    $iteration++
    $ts = Get-Date -Format "HH:mm:ss"
    Write-Host "--- [$ts] KPI #$iteration ---" -ForegroundColor Cyan
    python scripts_v6\kpi_monitor.py
    $next = (Get-Date).AddSeconds($INTERVAL).ToString("HH:mm:ss")
    Write-Host ""
    Write-Host "Next check: $next  (Ctrl+C to stop)" -ForegroundColor DarkGray
    Start-Sleep -Seconds $INTERVAL
}
