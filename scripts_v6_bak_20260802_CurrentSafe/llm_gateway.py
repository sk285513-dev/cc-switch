import time
import logging
import requests
from dataclasses import dataclass
from typing import Optional, Literal

from inflight_guard import build_inflight_key, acquire_inflight, release_inflight

Provider = Literal["vertexai", "aistudio"]
Stage = Literal["map", "reduce"]


@dataclass
class LLMResult:
    ok: bool
    text: Optional[str]
    error_code: Optional[str]
    error_message: Optional[str]
    degraded: bool
    attempts: int
    provider: str


def _call_with_timeout(func, timeout_sec, *args, **kwargs):
    import threading
    result_box = [None]
    error_box = [None]
    done_evt = threading.Event()

    def _target():
        try:
            result_box[0] = func(*args, **kwargs)
        except Exception as e:
            error_box[0] = e
        finally:
            done_evt.set()

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    fired = done_evt.wait(timeout_sec)
    if not fired:
        raise TimeoutError(f"{func.__name__} timed out after {timeout_sec}s")
    if error_box[0] is not None:
        raise error_box[0]
    return result_box[0]


def _is_timeout_error(exc: Exception) -> bool:
    err = str(exc).lower()
    return (
        "timed out" in err
        or "timeout" in err
        or "read operation" in err
        or "deadline exceeded" in err
        or "504" in err
    )


def _call_vertexai(*, prompt, timeout, config, use_search_grounding=False):
    import os
    from google import genai
    from google.genai import types
    from workflow_helper import load_config
    from model_router import get_router

    router = get_router()
    local_config = load_config()
    v_project = local_config.get("settings", {}).get("vertexai_project") or local_config.get("api", {}).get("vertexai_project")
    v_loc = local_config.get("settings", {}).get("vertexai_location") or local_config.get("api", {}).get("vertexai_location", "us-central1")
    v_cred_path = local_config.get("settings", {}).get("vertexai_credentials_path") or local_config.get("api", {}).get("vertexai_credentials_path", "")
    if v_cred_path:
        full_cred_path = os.path.normpath(
            os.path.join(
                local_config.get("paths", {}).get("project_root", "C:\\LocalAI_Workstation"),
                v_cred_path,
            )
        )
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = full_cred_path

    v_model = config.get("api", {}).get("gemini_model_high_accuracy", "gemini-2.5-flash")
    tool_objs = [{"google_search": {}}] if use_search_grounding else None

    logging.info(
        f"[DEBUG] Provider route: vertexai, "
        f"model={v_model}, prompt_len={len(str(prompt))}"
    )

    client = genai.Client(
        vertexai=True,
        project=v_project,
        location=v_loc,
        http_options={"timeout": timeout},
    )
    v_model = config.get("api", {}).get("gemini_model_high_accuracy", "gemini-2.5-flash")
    tool_objs = [{"google_search": {}}] if use_search_grounding else None

    logging.info(
        f"[DEBUG] Provider route: vertexai, "
        f"model={v_model}, prompt_len={len(str(prompt))}"
    )

    last_err = None
    for attempt in range(1, 4):
        try:
            response = _call_with_timeout(
                client.models.generate_content,
                timeout,
                model=v_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    tools=tool_objs,
                ),
            )
            if not getattr(response, "text", None):
                raise ValueError("API returned empty text")
            router.report_success(v_model)
            return LLMResult(True, response.text, None, None, False, attempt, "vertexai")
        except Exception as e:
            router.report_error(v_model, e)
            last_err = e
            if "429" in str(e).lower() or "quota" in str(e).lower():
                time.sleep(30)
            else:
                time.sleep(5)

    if last_err and _is_timeout_error(last_err):
        return LLMResult(False, None, "VERTEX_TIMEOUT", str(last_err), False, 3, "vertexai")
    return LLMResult(False, None, "PROVIDER_FAILED", str(last_err or "unknown error"), False, 3, "vertexai")


def _call_aistudio(*, prompt, model_name, api_key, qm, timeout, use_search_grounding=False):
    from model_router import get_router
    logging.info(
        f"[DEBUG] Provider route: aistudio, "
        f"model={model_name}, prompt_len={len(str(prompt))}"
    )
    router = get_router()
    last_err = None
    now = time.time()
    required_interval = 30.0 if "pro" in model_name else 5.0
    from merge_transcript import LAST_CALL_TIMES
    elapsed = now - LAST_CALL_TIMES.get(model_name, 0)
    if elapsed < required_interval:
        time.sleep(required_interval - elapsed)
    LAST_CALL_TIMES[model_name] = time.time()

    attempt = 0
    consecutive_429 = 0
    while True:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        if use_search_grounding:
            payload["tools"] = [{"googleSearch": {}}]
        if qm:
            qm.throttle_key(api_key)
        try:
            response = _call_with_timeout(
                requests.post,
                timeout,
                url,
                json=payload,
                timeout=timeout,
            )
            if response.status_code == 200:
                data = response.json()
                text = data["candidates"][0]["content"][0]["parts"][0]["text"]
                router.report_success(model_name)
                return LLMResult(True, text, None, None, False, attempt + 1, "aistudio")
            if response.status_code == 429:
                raise Exception(f"429 Too Many Requests: {response.text}")
            if response.status_code == 401:
                raise Exception(f"401 Unauthorized: {response.text}")
            if response.status_code == 400:
                # User wants actual model_name, request URL, payload JSON structure, and full body
                import copy
                safe_payload = copy.deepcopy(payload)
                if "contents" in safe_payload and safe_payload["contents"]:
                    for part in safe_payload["contents"][0].get("parts", []):
                        if "text" in part:
                            part["text"] = "[PROMPT_TEXT_REDACTED]"
                import json
                debug_info = f"\n[AIStudio 400 DEBUG]\nmodel_name: {model_name}\nURL: {url}\npayload_structure: {json.dumps(safe_payload, indent=2)}\nresponse_body: {response.text}\n"
                raise RuntimeError(f"HTTP 400: {response.text} {debug_info}")
            raise RuntimeError(f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            err_str = str(e)
            if qm and ("429" in err_str or "resource_exhausted" in err_str.lower() or "quota" in err_str.lower() or "401" in err_str):
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    consecutive_429 += 1
                res = qm.handle_error(e, api_key, consecutive_429, exclusive=True)
                if res.get("project_cooldown"):
                    consecutive_429 = 0
                if res.get("sleep_time", 0) > 0:
                    time.sleep(res["sleep_time"])
                if res.get("new_key") and res["new_key"] != api_key:
                    api_key = res["new_key"]
                    consecutive_429 = 0
                continue
            router.report_error(model_name, e)
            last_err = e
            attempt += 1
            if attempt >= 3:
                break
            time.sleep(5)

    if last_err and _is_timeout_error(last_err):
        return LLMResult(False, None, "AISTUDIO_TIMEOUT", str(last_err), False, attempt, "aistudio")
    return LLMResult(False, None, "PROVIDER_FAILED", str(last_err or "unknown error"), False, attempt, "aistudio")


def call_llm_with_resilience(*, stage: Stage, task_id: str, chunk_id: str, prompt: str, model_name: str, api_key: str, qm, timeout: float = 120.0, use_search_grounding: bool = False) -> LLMResult:
    from workflow_helper import load_config
    config = load_config()
    merge_engine = config.get("settings", {}).get("merge_engine", "gemini")
    logging.info(
        f"[DEBUG] Gateway entry: stage={stage}, "
        f"task_id={task_id}, chunk_id={chunk_id}, "
        f"merge_engine={merge_engine}, model_name={model_name}"
    )
    key = build_inflight_key("merge", stage, task_id, chunk_id)
    import os
    v_project = config.get("settings", {}).get("vertexai_project") or config.get("api", {}).get("vertexai_project")
    v_loc = config.get("settings", {}).get("vertexai_location") or config.get("api", {}).get("vertexai_location", "us-central1")
    v_cred = config.get("settings", {}).get("vertexai_credentials_path") or config.get("api", {}).get("vertexai_credentials_path", "")
    
    cred_display = "None"
    if v_cred:
        cred_full = os.path.normpath(os.path.join(config.get("paths", {}).get("project_root", "C:\\LocalAI_Workstation"), v_cred))
        cred_display = f"{os.path.basename(cred_full)} (Exists: {os.path.exists(cred_full)})"

    logging.warning(f"[LLM Gateway INIT] merge_engine={merge_engine}, vertexai_project={v_project}, vertexai_location={v_loc}, credentials_path={cred_display}, model_name={model_name}")

    if not acquire_inflight(key, owner=merge_engine, meta={"stage": stage, "task_id": task_id, "chunk_id": chunk_id}):
        logging.warning(f"[LLM Gateway] duplicate inflight request skipped: {key}")
        return LLMResult(False, None, "DUPLICATE_INFLIGHT", f"{key} already running", False, 0, merge_engine)

    try:
        if merge_engine == "vertexai":
            return _call_vertexai(
                prompt=prompt,
                timeout=timeout,
                config=config,
                use_search_grounding=use_search_grounding,
            )
        return _call_aistudio(
            prompt=prompt,
            model_name=model_name,
            api_key=api_key,
            qm=qm,
            timeout=timeout,
            use_search_grounding=use_search_grounding,
        )
    finally:
        release_inflight(key)
