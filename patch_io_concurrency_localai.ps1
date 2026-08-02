$ErrorActionPreference = "Stop"

$root        = "C:\LocalAI_Workstation"
$workflowPy  = Join-Path $root "scripts_v6\run_workflow.py"
$sttPy       = Join-Path $root "scripts_v6\stt_runner.py"
$stamp       = Get-Date -Format "yyyyMMdd_HHmmss"

foreach ($f in @($workflowPy, $sttPy)) {
    if (-not (Test-Path $f)) { throw "File not found: $f" }
    Copy-Item $f "$f.bak.$stamp" -Force
    Write-Host "Backed up: $f -> $f.bak.$stamp"
}

$content = Get-Content $workflowPy -Raw

$oldPattern = '(?ms)^(?<indent>[ \t]*)if \(\s*' +
              'not hasattr\(process_active_tasks, "executor"\)\s*' +
              '\r?\n\s*or getattr\(process_active_tasks, "executor_size", None\) != elastic_manager\.current\s*' +
              '\r?\n\s*\):\s*' +
              '\r?\n(?:[ \t]*\r?\n)?' +
              '[ \t]*if hasattr\(process_active_tasks, "executor"\):\s*' +
              '\r?\n[ \t]*process_active_tasks\.executor\.shutdown\(wait=False\)\s*' +
              '\r?\n[ \t]*process_active_tasks\.executor = ThreadPoolExecutor\(max_workers=elastic_manager\.current\)\s*' +
              '\r?\n[ \t]*process_active_tasks\.executor_size = elastic_manager\.current\s*' +
              '\r?\n[ \t]*process_active_tasks\.running_tasks = set\(\)'

$match = [regex]::Match($content, $oldPattern)

if ($match.Success) {
    $indent = $match.Groups['indent'].Value
    $newBlock = @"
${indent}if not hasattr(process_active_tasks, "executor"):
${indent}    process_active_tasks.executor = ThreadPoolExecutor(max_workers=elastic_manager.current)
${indent}    process_active_tasks.executor_size = elastic_manager.current
${indent}    process_active_tasks.running_tasks = set()
${indent}elif elastic_manager.current > process_active_tasks.executor_size:
${indent}    _old_executor = process_active_tasks.executor
${indent}    process_active_tasks.executor = ThreadPoolExecutor(max_workers=elastic_manager.current)
${indent}    process_active_tasks.executor_size = elastic_manager.current
${indent}    threading.Thread(target=lambda: _old_executor.shutdown(wait=True), daemon=True).start()
${indent}# NOTE: if elastic_manager.current <= executor_size (downscale), do nothing.
${indent}# Existing executor keeps running; fewer new tasks are simply submitted
${indent}# until it naturally matches the new target size.
"@
    $content = $content.Substring(0, $match.Index) + $newBlock + $content.Substring($match.Index + $match.Length)
    Set-Content -Path $workflowPy -Value $content -NoNewline -Encoding UTF8
    Write-Host "PATCHED: $workflowPy (expand-only executor logic applied)"
} else {
    Write-Warning "Pattern not found in $workflowPy ??no changes made. Please check manually."
}

$content2 = Get-Content $workflowPy -Raw
if ($content2 -notmatch '(?m)^\s*import threading\s*$') {
    $content2 = $content2 -replace '(?m)^(import .+?\r?\n)', "`$1import threading`r`n", 1
    Set-Content -Path $workflowPy -Value $content2 -NoNewline -Encoding UTF8
    Write-Host "Added missing 'import threading' to $workflowPy"
}

$sttContent = Get-Content $sttPy -Raw

$atomicHelper = @"

def atomic_json_dump(data, filepath, **kwargs):
    import json, os, tempfile
    directory = os.path.dirname(os.path.abspath(filepath)) or "."
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp_json_", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, **kwargs)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, filepath)
    except Exception:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise
"@

if ($sttContent -notmatch 'def atomic_json_dump\(') {
    $insertPattern = '(?ms)^(?:(?:import|from)\s.+\r?\n)+'
    $importMatch = [regex]::Match($sttContent, $insertPattern)
    if ($importMatch.Success) {
        $insertPos = $importMatch.Index + $importMatch.Length
        $sttContent = $sttContent.Substring(0, $insertPos) + $atomicHelper + "`r`n" + $sttContent.Substring($insertPos)
    } else {
        $sttContent = $atomicHelper + "`r`n" + $sttContent
    }
    Write-Host "Inserted atomic_json_dump() helper into $sttPy"
} else {
    Write-Host "atomic_json_dump() already present in $sttPy ??skipping"
}

$directDumpPattern = '(?ms)with open\((?<path>[^,]+),\s*["'']w["''][^)]*\)\s*as\s*(?<fh>\w+):\s*\r?\n\s*json\.dump\((?<data>[^,]+),\s*\k<fh>[^)]*\)'
$sttContent = [regex]::Replace($sttContent, $directDumpPattern, {
    param($m)
    "atomic_json_dump($($m.Groups['data'].Value), $($m.Groups['path'].Value))"
})

Set-Content -Path $sttPy -Value $sttContent -NoNewline -Encoding UTF8
Write-Host "PATCHED: $sttPy (atomic_json_dump applied where detected)"

Write-Host ""
Write-Host "=== Patch complete ===  Backups suffix: .bak.$stamp"
