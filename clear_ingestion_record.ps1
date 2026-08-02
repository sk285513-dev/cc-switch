<#
.SYNOPSIS
清除指定教材檔案在「全域指紋帳本」中的已處理紀錄。
.DESCRIPTION
如果您刻意想將同一個影片或檔案重新跑一次 AI 攝入管線，請使用此腳本。
它會透過 Fast Hash 算出該檔案的指紋，並從 SQLite 帳本中將其刪除。
#>

[CmdletBinding()]
param (
    [Parameter(Mandatory=$true, HelpMessage="請輸入要重新處理的影片或檔案的絕對路徑")]
    [string]$FilePath
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$dbPath = "A:\manifests\ingestion_ledger.db"

if (-not (Test-Path $dbPath)) {
    Write-Host "資料庫 $dbPath 不存在！" -ForegroundColor Red
    exit
}

if (-not (Test-Path $FilePath)) {
    Write-Host "找不到要清除的檔案：$FilePath" -ForegroundColor Red
    exit
}

$pythonScript = @"
import sys
import sqlite3
import os

# 將 scripts 目錄加入 PATH
scripts_dir = r"C:\LocalAI_Workstation\scripts"
sys.path.append(scripts_dir)

try:
    from duplicate_guard import get_fast_fingerprint, DB_PATH
except ImportError as e:
    print(f"❌ 載入 duplicate_guard 失敗: {e}")
    sys.exit(1)

file_path = sys.argv[1]
fingerprint = get_fast_fingerprint(file_path)

if not fingerprint:
    print('❌ 無法計算指紋。')
    sys.exit(1)

print(f'🔍 計算出的檔案指紋: {fingerprint}')
try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM ledger WHERE fingerprint = ?', (fingerprint,))
    row = cursor.fetchone()

    if row:
        cursor.execute('DELETE FROM ledger WHERE fingerprint = ?', (fingerprint,))
        conn.commit()
        print('✅ 成功從全域帳本中移除該檔案的攝入紀錄！下次掃描時將會被重新攝入。')
    else:
        print('⚠️ 該檔案原本就不在帳本中，無需清除。')
    conn.close()
except Exception as e:
    print(f"❌ 資料庫操作失敗: {e}")
"@

$tempPy = Join-Path $env:TEMP "temp_clear_ledger.py"
# 強制使用 utf8BOM 確保 Python 讀取中文無誤
Set-Content -Path $tempPy -Value $pythonScript -Encoding utf8BOM

Write-Host "正在比對指紋並清除紀錄..." -ForegroundColor Cyan
python $tempPy $FilePath

Remove-Item $tempPy -ErrorAction SilentlyContinue
