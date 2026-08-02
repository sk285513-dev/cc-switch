param(
    [string]$DashboardPath = "C:\LocalAI_Workstation\scripts_v6\progress_dashboard.py",
    [string]$PythonExe = "C:\Python312\python.exe"
)

$ErrorActionPreference = 'Stop'

function Write-Info($msg) { Write-Host $msg -ForegroundColor Cyan }
function Write-Ok($msg) { Write-Host $msg -ForegroundColor Green }
function Write-WarnMsg($msg) { Write-Host $msg -ForegroundColor Yellow }
function Write-Fail($msg) { Write-Host $msg -ForegroundColor Red }

function Get-Timestamp { (Get-Date).ToString('yyyyMMdd_HHmmss') }

function Backup-File {
    param([string]$Path)
    $backup = "$Path.bak.$(Get-Timestamp)"
    Copy-Item -LiteralPath $Path -Destination $backup -Force
    $backup
}

function Restore-Backup {
    param([string]$BackupPath, [string]$TargetPath)
    Copy-Item -LiteralPath $BackupPath -Destination $TargetPath -Force
}

function Read-Utf8Raw {
    param([string]$Path)
    [System.IO.File]::ReadAllText($Path, [System.Text.UTF8Encoding]::new($false))
}

function Write-Utf8NoBom {
    param([string]$Path, [string]$Content)
    $normalized = $Content -replace "`r?`n", "`r`n"
    [System.IO.File]::WriteAllText($Path, $normalized, [System.Text.UTF8Encoding]::new($false))
}

function Invoke-PythonCompileCheck {
    param([string]$PythonExe, [string]$Path)
    $cmd = Get-Command $PythonExe -ErrorAction SilentlyContinue
    if (-not $cmd) {
        Write-WarnMsg "[VERIFY] python not found, skip: $Path"
        return
    }
    & $PythonExe -m py_compile $Path
    if ($LASTEXITCODE -ne 0) { throw "python compile failed: $Path" }
}

if (-not (Test-Path -LiteralPath $DashboardPath)) { throw "DashboardPath not found: $DashboardPath" }

$backup = Backup-File $DashboardPath

try {
    Write-Info "[PATCH] dashboard: $DashboardPath"
    $lines = [System.IO.File]::ReadAllLines($DashboardPath, [System.Text.Encoding]::UTF8)

    # ---- Patch 1: task-level chunks read guard ----
    $s1 = -1
    $e1 = -1
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match 'cm = str\(mf\)\.replace\("\.json","_chunks\.json"\)') {
            $s1 = $i
        }
        if ($s1 -ge 0 -and $lines[$i] -match '^\s*except Exception:\s*$' -and $i -gt $s1) {
            $e1 = $i + 1
            break
        }
    }

    if ($s1 -ge 0 -and $e1 -ge 0 -and -not ($lines[$s1..$e1] -join "`n").Contains('for attempt in range(5)')) {
        $indent = ($lines[$s1] -replace '^(\s*).*', '$1')
        $inner = $indent + '    '
        $new1 = @(
            "${indent}cm = str(mf).replace(`".json`",`"_chunks.json`")",
            "${indent}n_chunks = done_chunks = 0",
            "${indent}if os.path.exists(cm):",
            "${inner}chunks = None",
            "${inner}for attempt in range(5):",
            "${inner}    try:",
            "${inner}        with open(cm, encoding=`"utf-8-sig`") as f:",
            "${inner}            chunks = json.load(f)",
            "${inner}        if not isinstance(chunks, list):",
            "${inner}            chunks = []",
            "${inner}        break",
            "${inner}    except (PermissionError, json.JSONDecodeError, OSError):",
            "${inner}        time.sleep(0.2 * (attempt + 1))",
            "${inner}    except Exception:",
            "${inner}        chunks = []",
            "${inner}        break",
            "",
            "${inner}if chunks is not None:",
            "${inner}    n_chunks = len(chunks)",
            "${inner}    done_chunks = sum(",
            "${inner}        1 for c in chunks",
            "${inner}        if isinstance(c, dict) and c.get(`"status`") == `"completed`"",
            "${inner}    )"
        )
        $before = $lines[0..($s1 - 1)]
        $after = $lines[($e1 + 1)..($lines.Count - 1)]
        $lines = $before + $new1 + $after
        Write-Ok "[dashboard-task-chunks-guard] replaced."
    } else {
        Write-Ok "[dashboard-task-chunks-guard] already patched or anchor not found, skip."
    }

    # ---- Patch 2: active chunks read guard ----
    $s2 = -1
    $e2 = -1
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match 'for mf in MANIFESTS_DIR\.glob\("\*_chunks\.json"\):') {
            $s2 = $i
        }
        if ($s2 -ge 0 -and $lines[$i] -match '^\s*except Exception:\s*$' -and $i -gt $s2) {
            $e2 = $i + 1
            break
        }
    }

    if ($s2 -ge 0 -and $e2 -ge 0 -and -not ($lines[$s2..$e2] -join "`n").Contains('for attempt in range(5)')) {
        $indent = ($lines[$s2] -replace '^(\s*).*', '$1')
        $inner = $indent + '    '
        $new2 = @(
            "${indent}for mf in MANIFESTS_DIR.glob(`"*_chunks.json`"):",
            "${inner}c_list = None",
            "${inner}for attempt in range(5):",
            "${inner}    try:",
            "${inner}        with open(mf, encoding=`"utf-8-sig`") as f:",
            "${inner}            c_list = json.load(f)",
            "${inner}        break",
            "${inner}    except (PermissionError, json.JSONDecodeError, OSError):",
            "${inner}        time.sleep(0.2 * (attempt + 1))",
            "${inner}    except Exception:",
            "${inner}        c_list = []",
            "${inner}        break",
            "",
            "${inner}if isinstance(c_list, list):",
            "${inner}    for c in c_list:",
            "${inner}        if isinstance(c, dict) and c.get(`"status`") == `"processing`":",
            "${inner}            started_at = c.get(`"started_at`", time.time())",
            "${inner}            active_chunks.append({`"filename`": c.get(`"filename`"), `"elapsed`": time.time() - started_at})"
        )
        $before = $lines[0..($s2 - 1)]
        $after = $lines[($e2 + 1)..($lines.Count - 1)]
        $lines = $before + $new2 + $after
        Write-Ok "[dashboard-active-chunks-guard] replaced."
    } else {
        Write-Ok "[dashboard-active-chunks-guard] already patched or anchor not found, skip."
    }

    [System.IO.File]::WriteAllLines($DashboardPath, $lines, [System.Text.UTF8Encoding]::new($false))

    Invoke-PythonCompileCheck -PythonExe $PythonExe -Path $DashboardPath

    Write-Ok "[SUCCESS] patch_state_machine_localai.ps1 done."
    Write-Host "Backup-Dashboard: $backup"
}
catch {
    Write-Fail "[ROLLBACK] error occurred. $_"
    Restore-Backup -BackupPath $backup -TargetPath $DashboardPath
    throw
}