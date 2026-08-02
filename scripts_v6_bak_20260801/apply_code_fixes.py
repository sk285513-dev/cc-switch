import sys
import os

merge_path = r'C:\LocalAI_Workstation\scripts_v6\merge_transcript.py'

with open(merge_path, 'r', encoding='utf-8-sig') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    line_num = i + 1
    if line_num == 2:
        new_lines.append('import sys\n')
    elif line_num in [12, 14, 19, 20]:
        pass # delete duplicate imports
    elif line_num == 425:
        break # stop here for merge_workflow
    else:
        new_lines.append(line)

new_merge_workflow = '''def merge_workflow(task_id):
    paths = ensure_dirs()
    manifests_dir = paths["manifests_dir"]
    chunks_dir = paths["chunks_dir"]
    task_chunks_dir = os.path.join(chunks_dir, task_id)

    manifest_file = os.path.join(manifests_dir, f"{task_id}.json")
    chunks_manifest_file = os.path.join(manifests_dir, f"{task_id}_chunks.json")

    if not os.path.exists(manifest_file) or not os.path.exists(chunks_manifest_file):
        log_error(f"Manifest or chunks manifest missing for {task_id}")
        return False

    with ManifestManager(manifest_file) as mm:
        manifest = mm.read() or {}
    with ManifestManager(chunks_manifest_file) as mm:
        chunks = mm.read() or []

    qm = QuotaManager()
    api_key = None
    raw_chunks = []

    try:
        try:
            api_key = qm.acquire_key_exclusive()
        except Exception as e:
            log_error(f"Merge Agent: 無法取得排他性 API 金鑰 ({e})，任務將保留，稍後重試。")
            return False

        log_workflow(f"Merge Agent: Reading and concatenating {len(chunks)} chunks...")

        total_chunks = len(chunks)

        if total_chunks == 0:
            log_error("Merge Agent: [GUARD] No chunk data found, reset task to chunked for STT retry")
            manifest["status"] = "chunked"
            manifest.setdefault("steps", {})
            manifest["steps"]["stt"] = "pending"
            manifest["steps"].pop("merge", None)
            manifest["steps"].pop("formatter", None)
            with ManifestManager(manifest_file) as mm:
                mm.write(manifest)
            return False

        done_txt = 0
        for chk in chunks:
            chk_path = chk.get("path", "")
            if not chk_path:
                continue
            stem = Path(chk_path).stem
            chk_txt = os.path.join(task_chunks_dir, f"{stem}.txt")
            if os.path.exists(chk_txt):
                done_txt += 1

        completion_rate = done_txt / total_chunks if total_chunks > 0 else 0.0

        if completion_rate < 0.85:
            log_error(
                f"Merge Agent: [GUARD] STT 完成率不足！"
                f"{done_txt}/{total_chunks} = {completion_rate*100:.0f}% < 85%，"
                f"拒絕合併，重置任務為 chunked 等待重跑 STT"
            )
            manifest["status"] = "chunked"
            manifest.setdefault("steps", {})
            manifest["steps"]["stt"] = "pending"
            manifest["steps"].pop("merge", None)
            manifest["steps"].pop("formatter", None)
            with ManifestManager(manifest_file) as mm:
                mm.write(manifest)
            return False

        log_workflow(
            f"Merge Agent: STT 完成率 {done_txt}/{total_chunks} = {completion_rate*100:.0f}% >= 85%，開始合併"
        )

        import time as _time
        map_timeout_count = 0
        map_start_ts = _time.time()

        merged_full_text = ""
        merged_cleaned_text = ""

        for chunk in chunks:
            chunk_path = chunk.get("path", "")
            if not chunk_path:
                continue
            stem = Path(chunk_path).stem
            chunk_txt_file = os.path.join(task_chunks_dir, f"{stem}.txt")
            if os.path.exists(chunk_txt_file):
                with open(chunk_txt_file, "r", encoding="utf-8-sig", errors="replace") as rf:
                    raw_text = rf.read().strip()
                    raw_chunks.append(raw_text)

        non_empty_raw_chunks = [c for c in raw_chunks if c and c.strip()]
        if not non_empty_raw_chunks:
            log_error("Merge Agent: [GUARD] raw_chunks are empty after TXT loading, reset task to chunked")
            manifest["status"] = "chunked"
            manifest.setdefault("steps", {})
            manifest["steps"]["stt"] = "pending"
            manifest["steps"].pop("merge", None)
            manifest["steps"].pop("formatter", None)
            with ManifestManager(manifest_file) as mm:
                mm.write(manifest)
            return False

        raw_chunks = non_empty_raw_chunks
        merged_full_text = "\\n".join(raw_chunks)

        for idx, chunk_content in enumerate(raw_chunks):
            cleaned_chunk = chunk_content

            log_workflow(f"Merge Agent: 正在執行切片 {idx+1}/{len(raw_chunks)} 的去冗餘與排版 (Map)...")
            try:
                from model_router import get_router as _get_router
                current_model = _get_router().acquire()
                cleaned_chunk = call_gemini_api(
                    PROMPT_CLEAN.format(text=chunk_content),
                    current_model,
                    api_key,
                    qm
                )
            except Exception as ce:
                err_str = str(ce).lower()
                log_error(f"Merge Agent: 切片 {idx+1} 去冗餘失敗: {ce}. fallback to raw chunk.")
                if (
                    "vertex_timeout:" in err_str
                    or "timed out" in err_str
                    or "timeout" in err_str
                    or "read operation" in err_str
                    or "deadline exceeded" in err_str
                    or "504" in err_str
                ):
                    map_timeout_count += 1
                cleaned_chunk = chunk_content

            total_elapsed = _time.time() - map_start_ts
            if map_timeout_count >= 3 or total_elapsed >= 600:
                log_error(
                    f"Merge Agent: 觸發全局 raw_fallback, "
                    f"map_timeout_count={map_timeout_count}, total_elapsed={round(total_elapsed, 3)}"
                )
                apply_raw_fallback(task_id, manifest, raw_chunks, task_chunks_dir, manifest_file)
                return True

            if not merged_cleaned_text:
                merged_cleaned_text = cleaned_chunk
            else:
                chars1 = list(merged_cleaned_text)
                chars2 = list(cleaned_chunk)

                suffix_len = min(400, len(chars1))
                suffix = chars1[-suffix_len:]
                prefix_len = min(400, len(chars2))
                prefix = chars2[:prefix_len]

                matcher = difflib.SequenceMatcher(None, suffix, prefix)
                match = matcher.find_longest_match(0, suffix_len, 0, prefix_len)

                if match.size >= 12:
                    cut_idx1 = len(chars1) - suffix_len + match.a
                    part1 = "".join(chars1[:cut_idx1])
                    part2 = "".join(chars2[match.b:])

                    gap_left = part1[-400:] if len(part1) >= 400 else part1
                    gap_right = part2[:400] if len(part2) >= 400 else part2
                    raw_gap = gap_left + " [銜接點] " + gap_right

                    log_workflow(f"Merge Agent: 正在執行縫隙 {idx}/{len(raw_chunks)-1} 邊界平滑化 (Reduce)...")
                    try:
                        from model_router import get_router as _get_router
                        current_model = _get_router().acquire()
                        refined_gap = call_gemini_api(
                            PROMPT_GAP_REFINE.format(text=raw_gap),
                            current_model,
                            api_key,
                            qm
                        )
                        refined_gap = refined_gap.replace("[銜接點]", "").strip()
                        part1_base = part1[:-len(gap_left)] if len(part1) >= len(gap_left) else ""
                        part2_base = part2[len(gap_right):] if len(part2) >= len(gap_right) else ""
                        merged_cleaned_text = part1_base + refined_gap + part2_base
                    except Exception as ge:
                        err_str = str(ge).lower()
                        log_error(f"Merge Agent: 邊界縫隙 {idx} 精校失敗: {ge}. fallback to direct merge.")
                        if (
                            "vertex_timeout:" in err_str
                            or "timed out" in err_str
                            or "timeout" in err_str
                            or "read operation" in err_str
                            or "deadline exceeded" in err_str
                            or "504" in err_str
                        ):
                            map_timeout_count += 1
                        merged_cleaned_text = part1 + part2
                else:
                    merged_cleaned_text = merged_cleaned_text + "\\n" + cleaned_chunk

            total_elapsed = _time.time() - map_start_ts
            if map_timeout_count >= 3 or total_elapsed >= 600:
                log_error(
                    f"Merge Agent: Reduce/Map 累積超時，觸發全局 raw_fallback, "
                    f"map_timeout_count={map_timeout_count}, total_elapsed={round(total_elapsed, 3)}"
                )
                apply_raw_fallback(task_id, manifest, raw_chunks, task_chunks_dir, manifest_file)
                return True

        if not merged_cleaned_text or not merged_cleaned_text.strip():
            log_error("Merge Agent: merged_cleaned_text is empty, switching to raw_fallback")
            apply_raw_fallback(task_id, manifest, raw_chunks, task_chunks_dir, manifest_file)
            return True

        merged_full_text = apply_glossary_fix(merged_full_text)
        merged_cleaned_text = apply_glossary_fix(merged_cleaned_text)

        out_full_path = os.path.join(task_chunks_dir, "merged_full_transcript.txt")
        with open(out_full_path, "w", encoding="utf-8-sig", errors="replace") as wf:
            wf.write(merged_full_text)

        out_cleaned_path = os.path.join(task_chunks_dir, "merged_cleaned_transcript.txt")
        with open(out_cleaned_path, "w", encoding="utf-8-sig", errors="replace") as wf:
            wf.write(merged_cleaned_text)

        safe_cleaned_text = merged_cleaned_text[:1000000]
        try:
            from model_router import get_router as _get_router
            current_model = _get_router().acquire()
            summary_text = call_gemini_api(
                PROMPT_SUMMARY.format(text=safe_cleaned_text),
                current_model,
                api_key,
                qm,
                use_search_grounding=True
            )
        except Exception as e:
            log_error(f"Merge Agent: Global summary failed: {e}. Fallback to template.")
            summary_text = "### 📖 全局章節大綱 (摘要生成遇限失敗)\\n"

        out_summary_path = os.path.join(task_chunks_dir, "merged_summary.txt")
        with open(out_summary_path, "w", encoding="utf-8-sig", errors="replace") as wf:
            wf.write(summary_text)

        manifest.setdefault("steps", {})
        manifest["steps"]["merge"] = "completed"
        manifest["status"] = "merged"
        manifest.setdefault("paths", {})
        manifest["paths"].update({
            "merged_full_transcript": out_full_path,
            "merged_cleaned_transcript": out_cleaned_path,
            "merged_summary": out_summary_path
        })

        with ManifestManager(manifest_file) as mm:
            mm.write(manifest)

        log_workflow(f"Merge Agent: Completed merge workflow for {task_id}")
        return True

    except Exception as e:
        log_error(f"Merge Agent: Unexpected error: {e}")
        try:
            if raw_chunks:
                log_error("Merge Agent: Unexpected error occurred, switching to emergency raw_fallback.")
                apply_raw_fallback(task_id, manifest, raw_chunks, task_chunks_dir, manifest_file)
                return True
        except Exception as fallback_err:
            log_error(f"Merge Agent: emergency raw_fallback also failed: {fallback_err}")

        manifest.setdefault("steps", {})
        manifest["steps"]["merge"] = "failed"
        manifest["status"] = "chunked"
        try:
            with ManifestManager(manifest_file) as mm:
                mm.write(manifest)
        except Exception as write_err:
            log_error(f"Merge Agent: failed to persist failed manifest state: {write_err}")

        return False

    finally:
        try:
            if api_key:
                qm.release_key(api_key)
        except Exception as release_err:
            log_error(f"Merge Agent: release_key failed: {release_err}")
'''

new_lines.append(new_merge_workflow)
new_lines.append('\n')

# Append anything after merge_workflow
for line in lines[668:]:
    new_lines.append(line)

with open(merge_path, 'w', encoding='utf-8-sig') as f:
    f.writelines(new_lines)

restart_path = r'C:\LocalAI_Workstation\restart_workflow.ps1'
restart_content = '''$ErrorActionPreference = "Stop"

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:LEXMIND_ENTERPRISE = "1"

$root = "C:\\LocalAI_Workstation"
$stdoutLog = "A:\\logs\\run_workflow_stdout.log"
$stderrLog = "A:\\logs\\run_workflow_stderr.log"
$workflowLog = "A:\\logs\\workflow.log"
$lockFile = "A:\\manifests\\workflow.lock"
$quotaState = "config\\quota_state.json"

Write-Host "=== LexMind Workflow Safe Restart ===" -ForegroundColor Cyan

function Get-PythonProcesses {
    Get-WmiObject Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'"
}

function Get-WorkflowProcess {
    Get-PythonProcesses | Where-Object { $_.CommandLine -match "scripts_v6\\\\run_workflow\\.py" }
}

function Get-WatchdogProcess {
    Get-PythonProcesses | Where-Object { $_.CommandLine -match "scripts_v6\\\\watchdog\\.py" }
}

$killed = 0
Get-PythonProcesses | ForEach-Object {
    $cmd = $_.CommandLine
    if ($null -eq $cmd) { return }

    if ($cmd -match "scripts_v6\\\\run_workflow\\.py") {
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

$proc = Start-Process python `
    -ArgumentList "scripts_v6\\run_workflow.py" `
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

$wd = Get-WatchdogProcess
if (-not $wd) {
    $wdProc = Start-Process pythonw `
        -ArgumentList "scripts_v6\\watchdog.py" `
        -WorkingDirectory $root `
        -WindowStyle Hidden `
        -PassThru

    Start-Sleep -Seconds 2
    $wd = Get-WatchdogProcess

    if ($wd) {
        Write-Host "  [START] watchdog.py started PID=$($wdProc.Id)" -ForegroundColor Green
    }
    else {
        Write-Host "  [WARN] watchdog launch attempted, but process not confirmed." -ForegroundColor Yellow
    }
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
'''
with open(restart_path, 'w', encoding='utf-8') as f:
    f.write(restart_content)

print("Both files updated.")
