$ErrorActionPreference = "Stop"

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Ok($msg) { Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err($msg) { Write-Host "[FAIL] $msg" -ForegroundColor Red }

# 注意：根據實際系統，F 區塊對應的檔案為 progress_dashboard.py，G 區塊為 stt_runner.py
$monitorPath = "C:\LocalAI_Workstation\scripts_v6\progress_dashboard.py"
$sttPath = "C:\LocalAI_Workstation\scripts_v6\stt_runner.py"

Write-Info "步驟 1：驗證程式碼是否成功落地..."
$monitorText = Get-Content -Path $monitorPath -Raw -Encoding UTF8
$sttText     = Get-Content -Path $sttPath     -Raw -Encoding UTF8
$ok = $true

# 驗證 progress_dashboard.py (拔除 Emoji 版的正規表達式)
if ($monitorText -notmatch "V6_ENV" `
    -or $monitorText -notmatch "\[CHUNKS\]") {
    Write-Err "progress_dashboard.py 驗證失敗：找不到預期關鍵字 ([CHUNKS])"
    $ok = $false
} else { Write-Ok "progress_dashboard.py 驗證通過" }

# 驗證 stt_runner.py (收斂區塊是否寫入)
if ($sttText -notmatch "def manifest_writer_thread" `
    -or $sttText -notmatch "def process_single_chunk") {
    Write-Err "stt_runner.py 驗證失敗：找不到預期關鍵字"
    $ok = $false
} else { Write-Ok "stt_runner.py 驗證通過" }

Write-Info "步驟 2：依驗證結果確認完成..."
if (-not $ok) {
    Write-Warn "驗證失敗，需要手動介入與回滾..."
    Write-Err "請檢查上方錯誤"
    exit 2
}

# 拔除 Emoji (Rule 1)
Write-Ok "[OK] patch_state_machine.ps1 驗證腳本執行成功，核心防護修改全數上線！"
