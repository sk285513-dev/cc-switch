# [CRITICAL CROSS-FILE DEPENDENCY WARNING]
# Upstream: run_workflow.py
# Downstream: quota_manager.py, Gemini / Vertex AI
# Shared State: Chunks, API Keys, Transcripts, Manifests

import os
import sys
import json
import time
import queue
import logging
import threading
import traceback
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from google import genai
from google.genai import types

from quota_manager import QuotaManager
from whisper_pool import WhisperPool
from model_router import get_router
from workflow_helper import (
    load_config,
    get_resolved_paths,
    get_engine_config,
    log_workflow,
    log_error,
)
from manifest_manager import ManifestManager, update_manifest


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


CHUNK_CONCURRENCY = 3
API_TRANSCRIBE_TIMEOUT = 150
ERROR_LOG_LOCK = threading.Lock()


def atomic_json_dump(data, filepath):
    """
    僅供 chunk 的 sidecar JSON 使用。
    task manifest / chunks manifest 一律走 ManifestManager。
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = filepath.with_name(f"{filepath.name}.{os.getpid()}.{threading.get_ident()}.tmp")

    try:
        with open(tmp_path, "w", encoding="utf-8", errors="replace") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())

        for i in range(30):
            try:
                os.replace(tmp_path, filepath)
                return
            except PermissionError:
                if i == 29:
                    raise
                time.sleep(min((0.05 * (1.25 ** i)), 1.5))
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass


def call_with_timeout(func, timeout_sec, *args, **kwargs):
    result_box = [None]
    error_box = [None]
    done_evt = threading.Event()

    def target():
        try:
            result_box[0] = func(*args, **kwargs)
        except Exception as e:
            error_box[0] = e
        finally:
            done_evt.set()

    t = threading.Thread(target=target, daemon=True)
    t.start()

    fired = done_evt.wait(timeout_sec)
    if not fired:
        raise TimeoutError(f"{func.__name__} timeout after {timeout_sec}s")
    if error_box[0]:
        raise error_box[0]
    return result_box[0]


def _append_chunk_error(chunkerrorslog: str, line: str) -> None:
    with ERROR_LOG_LOCK:
        Path(chunkerrorslog).parent.mkdir(parents=True, exist_ok=True)
        with open(chunkerrorslog, "a", encoding="utf-8", errors="replace") as ef:
            ef.write(line.rstrip("\n") + "\n")


def _mask_key(key: str | None) -> str:
    if not key:
        return "None"
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:4]}...{key[-4:]}"


def _load_task_and_chunks(task_id: str, manifests_dir: str):
    manifest_path = Path(manifests_dir) / f"{task_id}.json"
    chunks_manifest_path = Path(manifests_dir) / f"{task_id}_chunks.json"

    with ManifestManager(manifest_path) as mm:
        manifest = mm.read_manifest()

    with ManifestManager(chunks_manifest_path) as mm:
        chunks = mm.read_manifest()

    if not isinstance(manifest, dict):
        raise RuntimeError(f"task manifest invalid: {manifest_path}")
    if not isinstance(chunks, list):
        raise RuntimeError(f"chunks manifest invalid: {chunks_manifest_path}")

    return manifest_path, chunks_manifest_path, manifest, chunks


def _update_chunk_status(chunks_manifest_path: Path, chunk_filename: str, patch: dict) -> bool:
    def updater(chunks):
        if not isinstance(chunks, list):
            chunks = []

        found = False
        for item in chunks:
            if isinstance(item, dict) and item.get("filename") == chunk_filename:
                item.update(patch)
                found = True
                break

        if not found:
            new_item = {"filename": chunk_filename}
            new_item.update(patch)
            chunks.append(new_item)

        return chunks

    updated = update_manifest(chunks_manifest_path, updater)
    return updated is not None


def _mark_task_transcribed(manifest_path: Path) -> bool:
    def updater(m: dict):
        m.setdefault("steps", {})
        m["steps"]["stt"] = "completed"
        m["status"] = "transcribed"
        m.pop("error", None)
        return m

    return update_manifest(manifest_path, updater) is not None


def _mark_task_chunked_retryable(manifest_path: Path, chunks_manifest_path: Path) -> bool:
    def task_updater(m: dict):
        m.setdefault("steps", {})
        m["status"] = "chunked"
        m["steps"]["stt"] = "pending"
        return m

    def chunks_updater(chunks):
        if not isinstance(chunks, list):
            return []
        for c in chunks:
            if isinstance(c, dict) and c.get("status") == "failed":
                c["status"] = "pending"
                c["retry_count"] = c.get("retry_count", 0)
        return chunks

    ok1 = update_manifest(manifest_path, task_updater) is not None
    ok2 = update_manifest(chunks_manifest_path, chunks_updater) is not None
    return ok1 and ok2


def _write_chunk_outputs(task_id: str, chunk: dict, transcription: str) -> None:
    chunk_path = Path(chunk["chunk_path"])
    txt_output_path = chunk_path.with_suffix(".txt")
    json_output_path = chunk_path.with_suffix(".json")

    with open(txt_output_path, "w", encoding="utf-8", errors="replace") as tf:
        tf.write(transcription or "")

    atomic_json_dump(
        {
            "task_id": task_id,
            "filename": chunk.get("filename"),
            "partno": chunk.get("partno", chunk.get("chunkid")),
            "transcription": transcription,
            "processed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        json_output_path,
    )


def transcribe_chunk(client, uploaded_file, config: dict, qm=None, apikey=None) -> str:
    router = get_router()
    model = router.acquire_model()

    prompt = (
        "你是專業的法律長音訊轉錄助手。"
        "請忠實轉錄音訊內容，保留原始語意，不要摘要，不要改寫，"
        "盡量修正常見同音字與法律術語，直接輸出純文字逐字稿。"
    )

    if qm is not None and apikey is not None:
        try:
            qm.throttle_key(apikey)
        except Exception:
            pass

    try:
        from google.genai import types as genai_types

        response = client.models.generate_content(
            model=model,
            contents=[uploaded_file, prompt],
            config=genai_types.GenerateContentConfig(
                temperature=0.2,
            ),
        )

        router.report_success(model)
        text = getattr(response, "text", None)
        if not text or not text.strip():
            raise ValueError("API returned empty transcription")
        return text
    except Exception as e:
        router.report_error(model, e)
        raise


def _build_client_and_part(config: dict, stt_engine: str, key: str | None, chunk_path: str):
    with open(chunk_path, "rb") as f:
        audio_data = f.read()

    uploaded_file = types.Part.from_bytes(data=audio_data, mime_type="audio/wav")

    if stt_engine == "vertexai":
        engine_cfg = get_engine_config(config)
        project = engine_cfg.get("vertexai_project")
        location = engine_cfg.get("vertexai_location") or "us-central1"
        client = genai.Client(vertexai=True, project=project, location=location)
        return client, uploaded_file

    client = genai.Client(api_key=key)
    return client, uploaded_file


def process_single_chunk(
    chunk: dict,
    task_id: str,
    chunks_manifest_path: Path,
    config: dict,
    chunkerrorslog: str,
    stt_engine: str,
    qm=None,
    exclusive_key: str | None = None,
) -> bool:
    chunk_filename = chunk.get("filename")
    chunk_path = chunk.get("chunk_path")
    retry_limit = int(config.get("settings", {}).get("stt_max_retries", 3) or 3)

    if not chunk_filename or not chunk_path:
        _append_chunk_error(
            chunkerrorslog,
            f"{time.strftime('%Y-%m-%d %H:%M:%S')} {task_id} invalid chunk metadata: {chunk}",
        )
        return False

    _update_chunk_status(
        chunks_manifest_path,
        chunk_filename,
        {
            "status": "processing",
            "started_at": time.time(),
            "updated_at": time.time(),
            "last_error": None,
        },
    )

    for attempt in range(retry_limit + 1):
        try:
            active_key = None
            if stt_engine == "gemini":
                active_key = exclusive_key
                if active_key is None and qm is not None:
                    active_key = qm.acquire_key_exclusive()

            client, uploaded_file = _build_client_and_part(config, stt_engine, active_key, chunk_path)

            transcription = call_with_timeout(
                transcribe_chunk,
                API_TRANSCRIBE_TIMEOUT,
                client,
                uploaded_file,
                config,
                qm if stt_engine == "gemini" else None,
                active_key if stt_engine == "gemini" else None,
            )

            _write_chunk_outputs(task_id, chunk, transcription)

            _update_chunk_status(
                chunks_manifest_path,
                chunk_filename,
                {
                    "status": "completed",
                    "updated_at": time.time(),
                    "retry_count": attempt,
                    "last_error": None,
                },
            )

            if stt_engine == "gemini" and qm is not None and active_key and exclusive_key is None:
                try:
                    qm.release_key(active_key)
                except Exception:
                    pass

            log_workflow(f"[STT] chunk completed: {task_id} / {chunk_filename}")
            return True

        except Exception as e:
            errstr = str(e)
            is_retryable = any(token in errstr for token in [
                "429", "503", "UNAVAILABLE", "deadline", "Deadline", "ResourceExhausted"
            ])

            _append_chunk_error(
                chunkerrorslog,
                f"{time.strftime('%Y-%m-%d %H:%M:%S')} {task_id} {chunk_filename} "
                f"attempt={attempt} error={type(e).__name__}: {errstr}",
            )

            _update_chunk_status(
                chunks_manifest_path,
                chunk_filename,
                {
                    "status": "retrying" if attempt < retry_limit else "failed",
                    "updated_at": time.time(),
                    "retry_count": attempt + 1,
                    "last_error": errstr,
                    "failed_at": time.time() if attempt >= retry_limit else None,
                },
            )

            if stt_engine == "gemini" and qm is not None and exclusive_key is None:
                try:
                    # 只有這個函式自己拿的 key 才在這裡處理；外部傳入 exclusive_key 不動
                    pass
                except Exception:
                    pass

            if attempt >= retry_limit or not is_retryable:
                log_error(f"[STT] chunk failed permanently: {task_id} / {chunk_filename} / {errstr}")
                return False

            backoff = min(5 * (attempt + 1), 30)
            time.sleep(backoff)

    return False


def run_stt(task_id: str, exclusive_key: str | None = None):
    config = load_config()
    paths = get_resolved_paths()
    manifests_dir = paths["manifests_dir"]
    logs_dir = paths["logs_dir"]
    workflowlog = os.path.join(logs_dir, "workflow.log")
    chunkerrorslog = os.path.join(logs_dir, "chunk_errors.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(workflowlog, encoding="utf-8"),
        ],
        force=True,
    )

    manifest_path, chunks_manifest_path, manifest, chunks = _load_task_and_chunks(task_id, manifests_dir)

    if not chunks:
        log_error(f"[STT] no chunks found for task {task_id}")
        return False

    engine_cfg = get_engine_config(config)
    stt_engine = (engine_cfg.get("stt_engine") or "gemini").lower()

    qm = None
    if stt_engine == "gemini":
        try:
            qm = QuotaManager()
        except Exception as e:
            log_error(f"[STT] QuotaManager init failed: {e}")
            qm = None

    pending_chunks = [c for c in chunks if isinstance(c, dict) and c.get("status") != "completed"]
    if not pending_chunks:
        _mark_task_transcribed(manifest_path)
        return True

    log_workflow(
        f"[STT] task {task_id} start, engine={stt_engine}, "
        f"pending_chunks={len(pending_chunks)}, exclusive_key={_mask_key(exclusive_key)}"
    )

    all_succeeded = True

    with ThreadPoolExecutor(max_workers=CHUNK_CONCURRENCY) as executor:
        futures = {
            executor.submit(
                process_single_chunk,
                chunk,
                task_id,
                chunks_manifest_path,
                config,
                chunkerrorslog,
                stt_engine,
                qm,
                exclusive_key,
            ): chunk
            for chunk in pending_chunks
        }

        for future in as_completed(futures):
            chunk = futures[future]
            chunk_filename = chunk.get("filename", "unknown")
            try:
                ok = future.result()
                if not ok:
                    all_succeeded = False
            except Exception as exc:
                all_succeeded = False
                _append_chunk_error(
                    chunkerrorslog,
                    f"{time.strftime('%Y-%m-%d %H:%M:%S')} {task_id} {chunk_filename} "
                    f"FutureError={type(exc).__name__}: {exc} Traceback={traceback.format_exc().strip()}",
                )
                _update_chunk_status(
                    chunks_manifest_path,
                    chunk_filename,
                    {
                        "status": "failed",
                        "updated_at": time.time(),
                        "last_error": str(exc),
                        "failed_at": time.time(),
                    },
                )

    if all_succeeded:
        _mark_task_transcribed(manifest_path)
        log_workflow(f"[STT] task {task_id} completed → transcribed")
        return True

    _mark_task_chunked_retryable(manifest_path, chunks_manifest_path)
    log_workflow(f"[STT] task {task_id} not fully completed → reset to chunked/pending for retry")
    return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("task_id", type=str, nargs="?", default=None)
    args = parser.parse_args()

    if args.task_id:
        ok = run_stt(args.task_id)
        sys.exit(0 if ok else 1)

    print("Usage: python stt_runner.py <task_id>")
    sys.exit(1)
</USER_REQUEST>
<ADDITIONAL_METADATA>
The current local time is: 2026-08-03T14:38:53+08:00.
</ADDITIONAL_METADATA>

