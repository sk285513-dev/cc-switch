# V6 Debug Handoff Report

## 致命錯誤：WinError 10106 (缺乏 I/O 導致 asyncio 崩潰)
**日誌來源**：`logs\run_workflow_stderr.log`
```text
C:\LocalAI_Workstation\scripts_v6\run_workflow.py:542: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
  _tw_now = _dt.datetime.utcnow() + _dt.timedelta(hours=8)
C:\LocalAI_Workstation\scripts_v6\run_workflow.py:266: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
  cutoff = _dt.utcnow() + _td(hours=8) - _td(minutes=3)
C:\LocalAI_Workstation\scripts_v6\run_workflow.py:371: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
  cutoff = datetime.utcnow() - timedelta(minutes=30)
[BOOTSTRAP] GOOGLE_CLOUD_PROJECT = 'project-bbb51788-254b-4ec3-ad7' (from config.yaml)
[BOOTSTRAP] GCLOUD_PROJECT = 'project-bbb51788-254b-4ec3-ad7' (from config.yaml)
[BOOTSTRAP] GOOGLE_CLOUD_PROJECT = 'project-bbb51788-254b-4ec3-ad7' (from config.yaml)
[BOOTSTRAP] GCLOUD_PROJECT = 'project-bbb51788-254b-4ec3-ad7' (from config.yaml)
Traceback (most recent call last):
  File "C:\LocalAI_Workstation\scripts_v6\run_workflow.py", line 75, in <module>
    from file_watcher import scan_new_files
  File "C:\LocalAI_Workstation\scripts_v6\file_watcher.py", line 11, in <module>
    from auto_ingest_bot import is_file_content_legal
  File "C:\LocalAI_Workstation\scripts_v6\auto_ingest_bot.py", line 73, in <module>
    from agent_core_pro import LocalLegalAgent
  File "C:\LocalAI_Workstation\scripts_v6\agent_core_pro.py", line 5, in <module>
    import chromadb
  File "C:\Python312\Lib\site-packages\chromadb\__init__.py", line 6, in <module>
    from chromadb.api.client import Client as ClientCreator
  File "C:\Python312\Lib\site-packages\chromadb\api\__init__.py", line 1, in <module>
    from chromadb.api.types import *  # noqa: F401, F403
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Python312\Lib\site-packages\chromadb\api\types.py", line 24, in <module>
    from pydantic import BaseModel, field_validator, model_validator
  File "C:\Python312\Lib\site-packages\pydantic\__init__.py", line 5, in <module>
    from ._migration import getattr_migration
  File "C:\Python312\Lib\site-packages\pydantic\_migration.py", line 4, in <module>
    from pydantic.warnings import PydanticDeprecatedSince20
  File "C:\Python312\Lib\site-packages\pydantic\warnings.py", line 5, in <module>
    from .version import version_short
  File "C:\Python312\Lib\site-packages\pydantic\version.py", line 7, in <module>
    from pydantic_core import __version__ as __pydantic_core_version__
  File "C:\Python312\Lib\site-packages\pydantic_core\__init__.py", line 31, in <module>
    from .core_schema import CoreConfig, CoreSchema, CoreSchemaType, ErrorType
  File "C:\Python312\Lib\site-packages\pydantic_core\core_schema.py", line 4367, in <module>
    @deprecated('`field_before_validator_function` is deprecated, use `with_info_before_validator_function` instead.')
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Python312\Lib\site-packages\typing_extensions.py", line 2997, in __call__
    import asyncio.coroutines
  File "C:\Python312\Lib\asyncio\__init__.py", line 43, in <module>
    from .windows_events import *
  File "C:\Python312\Lib\asyncio\windows_events.py", line 8, in <module>
    import _overlapped
OSError: [WinError 10106] 無法載入或初始化所要求的服務提供者。
[BOOTSTRAP] GOOGLE_CLOUD_PROJECT = 'project-bbb51788-254b-4ec3-ad7' (from config.yaml)
[BOOTSTRAP] GCLOUD_PROJECT = 'project-bbb51788-254b-4ec3-ad7' (from config.yaml)
Traceback (most recent call last):
  File "C:\LocalAI_Workstation\scripts_v6\run_workflow.py", line 75, in <module>
    from file_watcher import scan_new_files
  File "C:\LocalAI_Workstation\scripts_v6\file_watcher.py", line 11, in <module>
    from auto_ingest_bot import is_file_content_legal
  File "C:\LocalAI_Workstation\scripts_v6\auto_ingest_bot.py", line 73, in <module>
    from agent_core_pro import LocalLegalAgent
  File "C:\LocalAI_Workstation\scripts_v6\agent_core_pro.py", line 5, in <module>
    import chromadb
  File "C:\Python312\Lib\site-packages\chromadb\__init__.py", line 6, in <module>
    from chromadb.api.client import Client as ClientCreator
  File "C:\Python312\Lib\site-packages\chromadb\api\__init__.py", line 1, in <module>
    from chromadb.api.types import *  # noqa: F401, F403
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Python312\Lib\site-packages\chromadb\api\types.py", line 24, in <module>
    from pydantic import BaseModel, field_validator, model_validator
  File "C:\Python312\Lib\site-packages\pydantic\__init__.py", line 5, in <module>
    from ._migration import getattr_migration
  File "C:\Python312\Lib\site-packages\pydantic\_migration.py", line 4, in <module>
    from pydantic.warnings import PydanticDeprecatedSince20
  File "C:\Python312\Lib\site-packages\pydantic\warnings.py", line 5, in <module>
    from .version import version_short
  File "C:\Python312\Lib\site-packages\pydantic\version.py", line 7, in <module>
    from pydantic_core import __version__ as __pydantic_core_version__
  File "C:\Python312\Lib\site-packages\pydantic_core\__init__.py", line 31, in <module>
    from .core_schema import CoreConfig, CoreSchema, CoreSchemaType, ErrorType
  File "C:\Python312\Lib\site-packages\pydantic_core\core_schema.py", line 4367, in <module>
    @deprecated('`field_before_validator_function` is deprecated, use `with_info_before_validator_function` instead.')
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Python312\Lib\site-packages\typing_extensions.py", line 2997, in __call__
    import asyncio.coroutines
  File "C:\Python312\Lib\asyncio\__init__.py", line 43, in <module>
    from .windows_events import *
  File "C:\Python312\Lib\asyncio\windows_events.py", line 8, in <module>
    import _overlapped
OSError: [WinError 10106] 無法載入或初始化所要求的服務提供者。
```

## FILE: LexMind_V6_沙盒驗證版.ps1
```powershell
# ============================================================
#  LexMind-Omni  v2.1  (2026-07-21)  ASCII-safe edition
# ============================================================
$env:LEXMIND_ENV      = "v6_canary"
$env:LEXMIND_ENTERPRISE = "1"
$env:PYTHONUTF8       = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:LEXMIND_MANIFEST_DIR = "A:\manifests_v6"
$env:LEXMIND_LOG_DIR = "A:\logs_v6"
$env:LEXMIND_WORKDIR = "C:\LocalAI_Workstation"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

$ROOT = "C:\LocalAI_Workstation"
Set-Location $ROOT

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  LexMind-Omni  One-Click Startup  v2.1   " -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ── STEP 1: Kill stale processes ──────────────────────────────
Write-Host "[1/5] Killing stale processes (Nuclear Option)..." -ForegroundColor Yellow

try { taskkill /F /IM python.exe /T 2>&1 | Out-Null } catch {}
try { taskkill /F /IM pythonw.exe /T 2>&1 | Out-Null } catch {}
try { taskkill /F /IM node.exe /T 2>&1 | Out-Null } catch {}
try { taskkill /F /IM ffmpeg.exe /T 2>&1 | Out-Null } catch {}

Write-Host "  [OK] Killed all previous Python, Node, and FFmpeg processes." -ForegroundColor Green
Start-Sleep -Seconds 2

# ── STEP 1.5: Verify Code State Machine (patch_state_machine.ps1) ─
Write-Host "[1.5/5] Verifying Code Integrity..." -ForegroundColor Yellow
$verifyProcess = Start-Process powershell -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "$ROOT\patch_state_machine.ps1" -PassThru -Wait -WindowStyle Hidden
if ($verifyProcess.ExitCode -ne 0) {
    Write-Host "[ERROR] Code integrity verification failed! (Exit Code: $($verifyProcess.ExitCode))" -ForegroundColor Red
    Write-Host "Please check patch_state_machine.ps1 output." -ForegroundColor Red
    Write-Host "Aborting startup." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "  [OK] Code verification passed." -ForegroundColor Green

# ── STEP 2: Reset locks & quota ───────────────────────────────
Write-Host "[2/5] Resetting locks and quota..." -ForegroundColor Yellow

Remove-Item "$env:LEXMIND_MANIFEST_DIR\workflow.lock" -Force -ErrorAction SilentlyContinue
'{"exhausted_keys":[]}' | Out-File "$ROOT\config\quota_state.json" -Encoding UTF8 -NoNewline

Write-Host "  [OK] workflow.lock removed, quota_state.json reset" -ForegroundColor Green

# ── STEP 3: Background engines ────────────────────────────────
Write-Host "[3/5] Starting background engines..." -ForegroundColor Yellow

$wf = Get-CimInstance Win32_Process -Filter "Name LIKE 'python%.exe'" |
      Where-Object { $_.CommandLine -match "run_workflow" }
if ($wf) {
    Write-Host "  [SKIP] Workflow Engine already running  PID=$($wf.ProcessId)" -ForegroundColor DarkGray
} else {
    Start-Process "pythonw" `
        -ArgumentList "scripts_v6/run_workflow.py" `
        -WorkingDirectory $ROOT `
        -WindowStyle Hidden
    Write-Host "  [OK]   Workflow Engine started" -ForegroundColor Green
}

$wd = Get-CimInstance Win32_Process -Filter "Name LIKE 'python%.exe'" |
      Where-Object { $_.CommandLine -match "watchdog_monitor\.py" }
if ($wd) {
    Write-Host "  [SKIP] Watchdog already running  PID=$($wd.ProcessId)" -ForegroundColor DarkGray
} else {
    Start-Process "pythonw" `
        -ArgumentList "scripts_v6/watchdog_monitor.py" `
        -WorkingDirectory $ROOT `
        -WindowStyle Hidden
    Write-Host "  [OK]   Watchdog started" -ForegroundColor Green
}

$ah = Get-CimInstance Win32_Process -Filter "Name LIKE 'python%.exe'" |
      Where-Object { $_.CommandLine -match "auto_healer\.py" }
if ($ah) {
    Write-Host "  [SKIP] Auto Healer already running  PID=$($ah.ProcessId)" -ForegroundColor DarkGray
} else {
    Start-Process "pythonw" `
        -ArgumentList "scripts_v6/auto_healer.py" `
        -WorkingDirectory $ROOT `
        -WindowStyle Hidden
    Write-Host "  [OK]   Auto Healer started" -ForegroundColor Green
}

# ── STEP 4: Streamlit UI ──────────────────────────────────────
Write-Host "[4/5] Starting Streamlit UI..." -ForegroundColor Yellow

$st = Get-CimInstance Win32_Process -Filter "Name LIKE 'python%.exe'" |
      Where-Object { $_.CommandLine -match "streamlit" }
if ($st) {
    Write-Host "  [SKIP] Streamlit already running  PID=$($st.ProcessId)" -ForegroundColor DarkGray
} else {
    Start-Process powershell `
        -WindowStyle Normal `
        -ArgumentList @(
            "-NoProfile","-NoExit","-ExecutionPolicy","Bypass","-Command",
            "Clear-Host; Write-Host '=== 正在啟動企業級網頁控制面板 ===' -ForegroundColor Cyan; Set-Location '$ROOT'; streamlit run app_v6.py --server.port 8506 --theme.base=`"light`""
        ) `
        -WorkingDirectory $ROOT
    Write-Host "  [OK]   Streamlit starting..." -ForegroundColor Green
    Start-Sleep -Seconds 5
    # 開啟瀏覽器
    Start-Process "http://localhost:8506"
}

# ── STEP 5: Monitor windows ───────────────────────────────────
Write-Host "[5/5] Starting monitor windows..." -ForegroundColor Yellow

# SRE Watchdog
$sre = Get-CimInstance Win32_Process -Filter "Name LIKE 'python%.exe'" |
       Where-Object { $_.CommandLine -match "sre_watchdog" }
if ($sre) {
    Write-Host "  [SKIP] SRE Watchdog already running  PID=$($sre.ProcessId)" -ForegroundColor DarkGray
} else {
    Start-Process powershell `
        -WindowStyle Normal `
        -ArgumentList @(
            "-NoExit","-ExecutionPolicy","Bypass","-Command",
            "`$env:LEXMIND_ENV='v6_canary'; `$env:PYTHONUTF8='1'; Set-Location '$ROOT'; python scripts_v6\sre_watchdog.py"
        ) `
        -WorkingDirectory $ROOT
    Write-Host "  [OK]   SRE Watchdog opened" -ForegroundColor Green
}

# KPI Runner
$kpi = Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
       Where-Object { $_.CommandLine -match "kpi_runner" }
if ($kpi) {
    Write-Host "  [SKIP] KPI Monitor already running  PID=$($kpi.ProcessId)" -ForegroundColor DarkGray
} else {
    Start-Process powershell `
        -WindowStyle Normal `
        -ArgumentList @("-NoExit","-ExecutionPolicy","Bypass","-File","$ROOT\kpi_runner.ps1") `
        -WorkingDirectory $ROOT
    Write-Host "  [OK]   KPI Monitor opened" -ForegroundColor Green
}

# Progress Dashboard (統計報表)
$db = Get-CimInstance Win32_Process -Filter "Name LIKE 'python%.exe'" |
      Where-Object { $_.CommandLine -match "progress_dashboard" }
if ($db) {
    Write-Host "  [SKIP] Progress Dashboard already running  PID=$($db.ProcessId)" -ForegroundColor DarkGray
} else {
    Start-Process powershell `
        -WindowStyle Normal `
        -ArgumentList @(
            "-NoExit","-ExecutionPolicy","Bypass","-Command",
            "`$env:LEXMIND_ENV='v6_canary'; `$env:PYTHONUTF8='1'; Set-Location '$ROOT'; while (`$true) { try { python scripts_v6\progress_dashboard.py } catch {}; Write-Host '[自動重啟中，5 秒後重新整理...]' -ForegroundColor Yellow; Start-Sleep -Seconds 5 }"
        ) `
        -WorkingDirectory $ROOT
    Write-Host "  [OK]   Progress Dashboard (統計報表) opened" -ForegroundColor Green
}

# Workflow Log Tail
Write-Host "  [OK]   Workflow Log Monitor opened" -ForegroundColor Green
Start-Process powershell `
    -WindowStyle Normal `
    -ArgumentList @(
        "-NoExit","-ExecutionPolicy","Bypass","-Command",
        "Clear-Host; Write-Host '=== 正在即時監控主工作流進度 (workflow.log) ===' -ForegroundColor Yellow; Get-Content ""$env:LEXMIND_LOG_DIR\workflow.log"" -Encoding UTF8 -Wait -Tail 30"
    ) `
    -WorkingDirectory $ROOT

# ── Summary ───────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  All done! Check the following:           " -ForegroundColor Cyan
Write-Host "  1. Streamlit  -> http://localhost:8506   " -ForegroundColor Cyan
Write-Host "  2. SRE Watchdog  (PowerShell window)     " -ForegroundColor Cyan
Write-Host "  3. KPI Monitor   (PowerShell window)     " -ForegroundColor Cyan
Write-Host "  4. Dashboard     (PowerShell window)     " -ForegroundColor Cyan
Write-Host "                                           " -ForegroundColor Cyan
Write-Host "  Crawler: python bot_ultimate_real_crawler.py" -ForegroundColor DarkYellow
Write-Host "  Or:      double-click Launch_Crawler_UI.vbs" -ForegroundColor DarkYellow
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Window will close in 5 seconds..." -ForegroundColor Gray
Start-Sleep -Seconds 5
```

## FILE: restart_workflow.ps1
```powershell
$ErrorActionPreference = "Stop"

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:LEXMIND_ENTERPRISE = "1"
$env:LEXMIND_ENV = "v6_canary"

# 1. 顶部补：
$env:LEXMIND_WORKDIR = "C:\LocalAI_Workstation"
$env:LEXMIND_MANIFEST_DIR = "A:\manifests_v6"
$env:LEXMIND_LOG_DIR = "A:\logs_v6"

# 2. 修改变量定义
$root = $env:LEXMIND_WORKDIR
$logsDir = $env:LEXMIND_LOG_DIR
$manifestsDir = $env:LEXMIND_MANIFEST_DIR

$stdoutLog = Join-Path $logsDir "run_workflow_stdout.log"
$stderrLog = Join-Path $logsDir "run_workflow_stderr.log"
$workflowLog = Join-Path $logsDir "workflow.log"
$lockFile = Join-Path $manifestsDir "workflow.lock"
$quotaState = Join-Path $root "config\quota_state.json"

# 3. 补齐目录创建
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null
New-Item -ItemType Directory -Force -Path $manifestsDir | Out-Null

Write-Host "=== LexMind Workflow Safe Restart ===" -ForegroundColor Cyan

function Get-PythonProcesses {
    Get-WmiObject Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'"
}

function Get-WorkflowProcess {
    Get-PythonProcesses | Where-Object { $_.CommandLine -match "scripts_v6\\run_workflow\.py" }
}

function Get-WatchdogProcess {
    Get-PythonProcesses | Where-Object { $_.CommandLine -match "scripts_v6\\watchdog_monitor\.py" -or $_.CommandLine -match "scripts_v6\\watchdog\.py" }
}

$killed = 0
Get-PythonProcesses | ForEach-Object {
    $cmd = $_.CommandLine
    if ($null -eq $cmd) { return }

    if ($cmd -match "scripts_v6\\run_workflow\.py") {
        Write-Host "  [KILL] run_workflow PID=$($_.ProcessId)" -ForegroundColor Red
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        $killed++
    }
    elseif ($cmd -match "progress_dashboard") {
        Write-Host "  [SKIP] dashboard PID=$($_.ProcessId)" -ForegroundColor Green
    }
    elseif ($cmd -match "watchdog") {
        Write-Host "  [SKIP] watchdog PID=$($_.ProcessId)" -ForegroundColor Green
    }
    elseif ($cmd -match "kpi_monitor") {
        Write-Host "  [SKIP] kpi_monitor PID=$($_.ProcessId)" -ForegroundColor Green
    }
}

if ($killed -eq 0) {
    Write-Host "  (no workflow process running)" -ForegroundColor Gray
}

Start-Sleep -Seconds 2

if (Test-Path $lockFile) {
    Copy-Item $lockFile "$lockFile.bak" -Force -ErrorAction SilentlyContinue
    Remove-Item $lockFile -Force -ErrorAction SilentlyContinue
    Write-Host "  [CLEAN] workflow.lock removed" -ForegroundColor Yellow
}

if (Test-Path $quotaState) {
    Copy-Item $quotaState "$quotaState.bak" -Force -ErrorAction SilentlyContinue
}
'{"exhausted_keys":[]}' | Out-File $quotaState -Encoding UTF8 -NoNewline
Write-Host "  [RESET] quota_state.json cleared" -ForegroundColor Yellow

if (Test-Path $stdoutLog) { Remove-Item $stdoutLog -Force -ErrorAction SilentlyContinue }
if (Test-Path $stderrLog) { Remove-Item $stderrLog -Force -ErrorAction SilentlyContinue }

# 5. Start-Process automatically inherits $env:* variables in PowerShell
$proc = Start-Process python `
    -ArgumentList "scripts_v6\run_workflow.py" `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog `
    -WorkingDirectory $root `
    -WindowStyle Hidden `
    -PassThru

Write-Host "  [START] run_workflow.py launched PID=$($proc.Id)" -ForegroundColor Green

Start-Sleep -Seconds 6

$wf = Get-WorkflowProcess
if (-not $wf) {
    Write-Host "  [FAIL] run_workflow.py did not stay alive after launch." -ForegroundColor Red

    if (Test-Path $stderrLog) {
        Write-Host "`n--- stderr tail ---" -ForegroundColor Yellow
        Get-Content $stderrLog -Tail 30 -Encoding UTF8
    }

    if (Test-Path $stdoutLog) {
        Write-Host "`n--- stdout tail ---" -ForegroundColor Yellow
        Get-Content $stdoutLog -Tail 30 -Encoding UTF8
    }

    throw "Workflow restart failed: run_workflow.py is not running."
}
else {
    $wf | ForEach-Object {
        Write-Host "  [OK] run_workflow alive PID=$($_.ProcessId)" -ForegroundColor Green
    }
}

# 4. 彻底删除主动拉起 watchdog 的逻辑，只保留检测与提示
$wd = Get-WatchdogProcess
if (-not $wd) {
    Write-Host "  [WARN] watchdog_monitor is NOT running. Please start it separately." -ForegroundColor Yellow
}
else {
    $wd | ForEach-Object {
        Write-Host "  [OK] watchdog already alive PID=$($_.ProcessId)" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "--- workflow.log tail ---" -ForegroundColor Cyan
if (Test-Path $workflowLog) {
    Get-Content $workflowLog -Tail 10 -Encoding UTF8
}
else {
    Write-Host "workflow.log not found" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "--- stderr tail ---" -ForegroundColor Cyan
if (Test-Path $stderrLog) {
    Get-Content $stderrLog -Tail 10 -Encoding UTF8
}
else {
    Write-Host "(stderr log empty or not found)" -ForegroundColor Gray
}

```

## FILE: watchdog_monitor.py
```python
import os
import sys
import time
import json
import glob
import subprocess
import datetime
from pathlib import Path

# ── 設定 ──
WORKDIR = Path("C:/LocalAI_Workstation")
LOG_PATH = Path(os.environ.get("LEXMIND_LOG_DIR", "A:/logs_v6")) / "watchdog.log"
MANIFESTS_DIR = Path(os.environ.get("LEXMIND_MANIFEST_DIR", "A:/manifests_v6"))
WORKFLOW_LOCK = MANIFESTS_DIR / "workflow.lock"
CHECK_INTERVAL = 15 * 60   # 15 分鐘
PIPELINE_INTERVAL = 30     # 30 秒做一次 pipeline tick

os.chdir(WORKDIR)
sys.path.insert(0, str(WORKDIR / "scripts_v6"))

env = os.environ.copy()
env["PYTHONIOENCODING"] = "utf-8"
env["PYTHONUTF8"] = "1"
env["LEXMIND_ENV"] = "v6_canary"
env["LEXMIND_MANIFEST_DIR"] = str(MANIFESTS_DIR)

def log(msg: str):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_PATH, "a", encoding="utf-8-sig") as f:
            f.write(line + "\n")
    except Exception:
        pass

def is_workflow_alive() -> bool:
    """檢查 run_workflow.py 是否在 python 進程中存活。"""
    try:
        import psutil
        for p in psutil.process_iter(['name', 'cmdline']):
            try:
                name = p.info.get('name', '')
                cmdline = p.info.get('cmdline', [])
                if name and 'python' in name.lower() and cmdline:
                    if any('run_workflow' in str(arg) for arg in cmdline):
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False
    except Exception as e:
        log(f"[WARN] psutil failed, fallback to WMI: {e}")
        try:
            result = subprocess.run(
                ["powershell", "-c",
                 "Get-WmiObject Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" | "
                 "Where-Object {$_.CommandLine -match 'run_workflow'} | "
                 "Measure-Object | Select-Object -ExpandProperty Count"],
                capture_output=True, text=True, timeout=10, encoding="utf-8-sig", errors="ignore"
            )
            count = int(result.stdout.strip() or "0")
            if count > 0:
                return True
        except Exception:
            pass
        return WORKFLOW_LOCK.exists()

def restart_workflow():
    """重啟 run_workflow.py。"""
    log("[Watchdog] run_workflow.py 未偵測到！嘗試重啟...")
    try:
        WORKFLOW_LOCK.unlink(missing_ok=True)
    except Exception:
        pass
    (WORKDIR / "logs").mkdir(parents=True, exist_ok=True)
    
    _wf_stdout = open(str(WORKDIR / "logs" / "run_workflow_stdout.log"), "a", encoding="utf-8-sig")
    _wf_stderr = open(str(WORKDIR / "logs" / "run_workflow_stderr.log"), "a", encoding="utf-8-sig")
    proc = subprocess.Popen(
        [sys.executable, str(WORKDIR / "scripts_v6" / "run_workflow.py")],
        env=env, cwd=str(WORKDIR),
        stdout=_wf_stdout, stderr=_wf_stderr,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
    )
    log(f"[Watchdog] run_workflow.py 重啟完成 (pid={proc.pid})")

def run_auto_verify():
    """執行 auto_verify.py 並摘錄結果。"""
    try:
        result = subprocess.run(
            [sys.executable, str(WORKDIR / "scripts_v6" / "auto_verify.py")],
            capture_output=True, text=True, timeout=120, encoding="utf-8-sig", errors="ignore",
            env=env, cwd=str(WORKDIR)
        )
        if result.stdout:
            lines = result.stdout.splitlines()
            for line in lines:
                if any(kw in line for kw in ["驗收結論", "偵測到", "PASS", "FAIL", "ERROR"]):
                    log("[AutoVerify] " + line.strip())
    except Exception as e:
        log(f"[Watchdog] auto_verify 執行失敗: {e}")

def pipeline_tick():
    """補發卡住的 merge 和 formatter subprocess。"""
    spawned = 0
    for mf in MANIFESTS_DIR.glob("task_*.json"):
        if "_chunks" in mf.name:
            continue
        try:
            with open(mf, encoding="utf-8-sig") as f:
                m = json.load(f)
            task_id = m.get("task_id", "")
            steps = m.get("steps", {})
            status = m.get("status", "")
            if status in ("completed", "failed"):
                continue

            if steps.get("stt") == "completed" and steps.get("merge") == "pending":
                proc = subprocess.Popen(
                    [sys.executable, str(WORKDIR / "scripts_v6" / "merge_transcript.py"),
                     "--task-id", task_id],
                    env=env, cwd=str(WORKDIR),
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
                )
                log(f"[PipelineTick] Spawned merge for {task_id[-4:]} (pid={proc.pid})")
                spawned += 1

            elif steps.get("merge") == "completed" and steps.get("formatter") == "pending":
                proc = subprocess.Popen(
                    [sys.executable, str(WORKDIR / "scripts_v6" / "markdown_formatter.py"),
                     "--task-id", task_id],
                    env=env, cwd=str(WORKDIR),
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
                )
                log(f"[PipelineTick] Spawned formatter for {task_id[-4:]} (pid={proc.pid})")
                spawned += 1
        except Exception:
            pass
    if spawned:
        log(f"[PipelineTick] Total spawned: {spawned}")

def main():
    log("=" * 60)
    log("[Watchdog] LexMind-Omni 持久性監測程序啟動 (V6 Sandbox)")
    log("[Watchdog] 監測間隔: 15 分鐘（auto_verify + workflow 健康檢查）")
    log("[Watchdog] Pipeline tick 間隔: 30 秒")
    log(f"[Watchdog] Manifest Dir: {MANIFESTS_DIR}")
    log("=" * 60)

    last_verify = 0

    while True:
        now = time.time()
        pipeline_tick()

        if now - last_verify >= CHECK_INTERVAL:
            log("[Watchdog] === 15 分鐘定期檢查 ===")
            if not is_workflow_alive():
                restart_workflow()
            else:
                log("[Watchdog] run_workflow.py 存活 ✅")

            run_auto_verify()

            try:
                completed = sum(
                    1 for mf in MANIFESTS_DIR.glob("task_*.json")
                    if "_chunks" not in mf.name
                    and json.load(open(mf, encoding="utf-8-sig")).get("status") == "completed"
                )
                log(f"[Watchdog] 已完成任務: {completed}")
            except Exception:
                pass

            last_verify = now

        time.sleep(PIPELINE_INTERVAL)

if __name__ == "__main__":
    import io
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8-sig', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8-sig', errors='replace')
    main()

```

## FILE: run_workflow.py
```python
import os
import sys
import time
import json
import uuid
import shutil
import logging
import argparse
import subprocess
from pathlib import Path
from filelock import FileLock

sys.path.insert(0, str(Path("C:/LocalAI_Workstation/scripts_v6").resolve()))

import config
from utils import SingleInstanceLock
from process_video import extract_audio
from vad_chunker import detect_silences_and_chunk
from stt_runner import run_stt_for_task as run_stt
from merge_transcript import process_task as merge_workflow
from markdown_formatter import format_task as format_markdown
from error_analyzer import dump_stack_snapshot
from error_analyzer import recover_failed_task

# ── 強制讀取隔離區 ──
WORKDIR = os.environ.get("LEXMIND_WORKDIR", "C:/LocalAI_Workstation")
MANIFESTS_DIR = os.environ.get("LEXMIND_MANIFEST_DIR", "A:/manifests_v6")
LOGS_DIR = os.environ.get("LEXMIND_LOG_DIR", "A:/logs_v6")
CHUNKS_DIR = os.environ.get("LEXMIND_CHUNKS_DIR", "A:/chunks_v6")
PROCESSED_MD_DIR = os.environ.get("LEXMIND_PROCESSED_MD_DIR", "A:/processed_md_v6")
PROCESSED_SRT_DIR = os.environ.get("LEXMIND_PROCESSED_SRT_DIR", "A:/processed_srt_v6")
PROCESSING_DIR = os.environ.get("LEXMIND_PROCESSING_DIR", "A:/processing_v6")

def ensure_dirs():
    paths = {
        "logs": LOGS_DIR,
        "manifests_dir": MANIFESTS_DIR,
        "chunks_dir": CHUNKS_DIR,
        "processed_md": PROCESSED_MD_DIR,
        "output_srt": PROCESSED_SRT_DIR,
        "processing": PROCESSING_DIR
    }
    for p in paths.values():
        os.makedirs(p, exist_ok=True)
    return paths

def setup_logging():
    os.makedirs(LOGS_DIR, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(LOGS_DIR, "workflow.log"),
        level=logging.INFO,
        format="[%(asctime)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

def log_workflow(msg):
    print(msg, flush=True)
    logging.info(msg)

def log_error(msg):
    print(f"[ERROR] {msg}", file=sys.stderr, flush=True)
    logging.error(msg)

def atomic_json_dump(data, path):
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)

def get_exclusive_key():
    state_file = "config/quota_state.json"
    if not os.path.exists(state_file):
        return None
    try:
        with open(state_file, "r", encoding="utf-8") as f:
            state = json.load(f)
    except Exception:
        return None
        
    for model_group in config.GEMINI_API_KEYS.values():
        for key in model_group:
            if key not in state.get("exhausted_keys", []):
                return key
    return None

import glob

def scan_new_files():
    search_dirs = [
        "A:/media_input",
        "E:/", "F:/", "G:/", "H:/", "I:/", "J:/", "K:/", "M:/"
    ]
    supported_exts = {".mp3", ".mp4", ".wav"}

    existing_sources = set()
    for mf in glob.glob(os.path.join(MANIFESTS_DIR, "task_*.json")):
        if "_chunks" in mf:
            continue
        try:
            with open(mf, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
                existing_sources.add(data.get("source_file"))
        except Exception:
            pass

    for d in search_dirs:
        if not os.path.exists(d):
            continue
        for root_dir, _, files in os.walk(d):
            if any(skip in root_dir for skip in ["$RECYCLE.BIN", "System Volume Information", "Windows", "Program Files"]):
                continue
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in supported_exts:
                    abs_path = os.path.join(root_dir, file)
                    if abs_path not in existing_sources:
                        task_id = str(uuid.uuid4())
                        manifest_path = os.path.join(MANIFESTS_DIR, f"task_{task_id}.json")
                        manifest = {
                            "task_id": task_id,
                            "source_file": abs_path,
                            "source_name": file,
                            "status": "pending",
                            "created_at": time.time(),
                            "steps": {
                                "preprocess": "pending",
                                "chunk_planner": "pending",
                                "stt": "pending",
                                "merge": "pending",
                                "formatter": "pending"
                            }
                        }
                        try:
                            if os.path.getsize(abs_path) > 0:
                                atomic_json_dump(manifest, manifest_path)
                                log_workflow(f"Workflow Engine: Found new file -> {abs_path} (Task: {task_id})")
                                existing_sources.add(abs_path)
                        except Exception as e:
                            log_error(f"Cannot process {abs_path}: {e}")

def process_active_tasks(chunking_only=False):
    target_manifest = None
    target_data = None
    
    for mf in sorted(glob.glob(os.path.join(MANIFESTS_DIR, "task_*.json")), key=os.path.getctime):
        if "_chunks" in mf:
            continue
        try:
            with open(mf, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
                
            if data.get("status") == "chunked":
                target_manifest = mf
                target_data = data
                break
        except Exception:
            pass
            
    if not target_manifest:
        for mf in sorted(glob.glob(os.path.join(MANIFESTS_DIR, "task_*.json")), key=os.path.getctime):
            if "_chunks" in mf:
                continue
            try:
                with open(mf, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                    
                if data.get("status") == "pending":
                    target_manifest = mf
                    target_data = data
                    break
            except Exception:
                pass
                
    if not target_manifest:
        return False
        
    try:
        run_task(target_manifest, target_data, chunking_only)
        return True
    except Exception as e:
        log_error(f"Fatal error processing {target_manifest}: {str(e)}")
        import traceback
        traceback.print_exc()
        try:
            dump_stack_snapshot(target_data.get("task_id", "unknown"))
        except Exception:
            pass
        return False

def plan_chunks(manifest_path, data):
    task_id = data["task_id"]
    source_name = data["source_name"]
    processing_dir = os.path.join(PROCESSING_DIR, task_id)
    wav_path = os.path.join(processing_dir, f"{task_id}.wav")
    
    if not os.path.exists(wav_path):
        raise FileNotFoundError(f"WAV not found for {task_id}")
        
    log_workflow(f"Planning chunks for {task_id}...")
    chunk_list = detect_silences_and_chunk(wav_path, CHUNKS_DIR, task_id)
    
    chunks_manifest_path = os.path.join(MANIFESTS_DIR, f"task_{task_id}_chunks.json")
    chunks_data = {
        "task_id": task_id,
        "source_name": source_name,
        "chunks": chunk_list,
        "status": "pending",
        "created_at": time.time()
    }
    atomic_json_dump(chunks_data, chunks_manifest_path)
    
    data["steps"]["chunk_planner"] = "completed"
    data["status"] = "chunked"
    atomic_json_dump(data, manifest_path)
    log_workflow(f"Chunk planning complete for {task_id}. Generated {len(chunk_list)} chunks.")

def run_task(manifest_path, data, chunking_only=False):
    task_id = data["task_id"]
    source_file = data["source_file"]
    
    log_workflow(f"--- Starting task processing: {data['source_name']} ({task_id}) ---")
    
    if data["steps"]["preprocess"] == "pending":
        log_workflow("Step 1: Extracting audio...")
        processing_dir = os.path.join(PROCESSING_DIR, task_id)
        os.makedirs(processing_dir, exist_ok=True)
        out_wav = os.path.join(processing_dir, f"{task_id}.wav")
        
        success = extract_audio(source_file, out_wav)
        if success:
            data["steps"]["preprocess"] = "completed"
            atomic_json_dump(data, manifest_path)
        else:
            data["status"] = "failed"
            data["error"] = "Audio extraction failed"
            atomic_json_dump(data, manifest_path)
            return
            
    if data["steps"]["chunk_planner"] == "pending":
        log_workflow("Step 2: Planning chunks...")
        try:
            plan_chunks(manifest_path, data)
        except Exception as e:
            log_error(f"Chunk planning failed: {e}")
            data["status"] = "failed"
            data["error"] = str(e)
            atomic_json_dump(data, manifest_path)
            return

    if chunking_only:
        log_workflow(f"Task {task_id} paused at chunked state due to --chunking-only mode.")
        return

    chunks_manifest_path = os.path.join(MANIFESTS_DIR, f"task_{task_id}_chunks.json")
    if not os.path.exists(chunks_manifest_path):
        log_error(f"Chunks manifest missing for {task_id}. Cannot proceed.")
        return
        
    with open(chunks_manifest_path, "r", encoding="utf-8-sig") as f:
        chunks_data = json.load(f)

    if chunks_data.get("status") == "completed":
        data["steps"]["stt"] = "completed"
    else:
        if data["steps"]["stt"] == "pending":
            api_key = get_exclusive_key()
            if not api_key:
                log_error("No available Gemini API key. STT step skipped for now.")
                return
                
            log_workflow("Step 3: Running STT...")
            success = run_stt(chunks_manifest_path, api_key)
            if success:
                data["steps"]["stt"] = "completed"
                atomic_json_dump(data, manifest_path)
            else:
                log_error("STT step did not complete successfully.")
                return

    if data["steps"]["merge"] == "pending":
        log_workflow("Step 4: Merging transcripts (Mock)...")
        api_key = get_exclusive_key()
        if not api_key:
            log_error("No available Gemini API key for merge step. Skipped for now.")
            return
            
        success = merge_workflow(chunks_manifest_path, api_key)
        if success:
            data["steps"]["merge"] = "completed"
            atomic_json_dump(data, manifest_path)
            
            merged_json = os.path.join(CHUNKS_DIR, task_id, f"{task_id}_merged.json")
            if os.path.exists(merged_json):
                with open(merged_json, "r", encoding="utf-8") as f:
                    mj = json.load(f)
                
                md_path = os.path.join(PROCESSED_MD_DIR, f"{data['source_name']}.md")
                srt_path = os.path.join(PROCESSED_SRT_DIR, f"{data['source_name']}.srt")
                
                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(f"# {data['source_name']}\n\n")
                    f.write("This is a mock final markdown document generated by the pipeline.\n")
                    if "final_transcript" in mj:
                        f.write(mj["final_transcript"])
                        
                with open(srt_path, "w", encoding="utf-8") as f:
                    f.write("1\n00:00:00,000 --> 00:00:10,000\nMock Subtitle Line\n")
                    
        else:
            log_error("Merge step failed.")
            return

    if data["steps"]["formatter"] == "pending":
        log_workflow("Step 5: Formatting final output (Mock)...")
        data["steps"]["formatter"] = "completed"
        data["status"] = "completed"
        atomic_json_dump(data, manifest_path)
        log_workflow(f"*** Task {task_id} fully completed! ***")
        
        processing_dir = os.path.join(PROCESSING_DIR, task_id)
        if os.path.exists(processing_dir):
            shutil.rmtree(processing_dir, ignore_errors=True)

def run_loop(chunking_only=False):
    log_workflow("Workflow Engine: Started loop. Press Ctrl+C to exit.")
    while True:
        scan_new_files()
        processed_any = process_active_tasks(chunking_only)
        if not processed_any:
            time.sleep(10)

def main():
    setup_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--one-shot", action="store_true", help="Run once and exit instead of loop")
    parser.add_argument("--chunking-only", action="store_true", help="Only run local chunking steps (preprocess, chunk planner)")
    args = parser.parse_args()
    
    paths = ensure_dirs()
    lock_file = os.path.join(paths["manifests_dir"], "workflow.lock")
    lock = SingleInstanceLock(lock_file)
    
    if not lock.acquire():
        print(f"[Workflow Lock] Another instance of run_workflow is already running (locked on {lock_file}). Exiting.")
        sys.exit(0)
        
    try:
        if args.one_shot:
            log_workflow("Workflow Engine: Running in one-shot mode." + (" [ȤҦ]" if args.chunking_only else ""))
            scan_new_files()
            process_active_tasks(args.chunking_only)
        else:
            run_loop(args.chunking_only)
    finally:
        lock.release()

if __name__ == "__main__":
    main()

```
