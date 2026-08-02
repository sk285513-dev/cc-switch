"""
model_router.py — Gemini 模型路由代理 (Model Router Agent) v2
==============================================================
【職責】此模組是系統中唯一負責模型選擇與切換的單元：
  • 維護可用模型優先序列（依品質排序，實測確認）
  • 偵測 429 / 503 / 404 錯誤，動態調整各模型信賴度與冷卻時間
  • 追蹤失敗率，對高失敗率模型降低優先度
  • 持久化狀態至磁碟，重啟後無縫接續
  • 完全執行緒安全（可在並發 worker 中共用）
  • 提供 REST API 包裝器（call_rest），統一覆蓋直連 REST 的腳本

【使用方法 - SDK 呼叫（stt_runner.py）】
  from model_router import get_router
  router = get_router()
  model = router.acquire()
  try:
      result = client.models.generate_content(model=model, ...)
      router.report_success(model)
  except Exception as e:
      router.report_error(model, e)
      raise

【使用方法 - REST 呼叫（multimodal_input.py / visual_analyzer.py）】
  from model_router import rest_generate
  text = rest_generate(file_uri, mime_type, prompt, api_key)

【重要】有任何模型相關問題，只改本檔，不動其他腳本！
"""

from __future__ import annotations
try:
    import json
except ImportError:
    import json

import json
import logging
import os
import re
import threading
import time
from dataclasses import dataclass, asdict
from typing import Optional, Callable

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────
# 【2026-07-11 實測白名單】依品質降序排列
# ─────────────────────────────────────────────────────────────────
from workflow_helper import load_config
try:
    _config = load_config()
    _stt_engine = _config.get("settings", {}).get("stt_engine", "gemini")
except Exception as e:
    logger.warning(f"[ModelRouter] 讀取 config.yaml 失敗，預設回 fallback: {e}")
    _stt_engine = "gemini"
    _config = {}

_high = _config.get("api", {}).get("gemini_model_high_accuracy", "gemini-2.5-flash")
_low = _config.get("api", {}).get("gemini_model_low_cost", "gemini-2.5-flash")

if _stt_engine == "vertexai":
    # Vertex AI 使用專屬三級路由 (高階 -> 中低階)
    MODELS_BY_PRIORITY: list[str] = [_high, _low]
    # Vertex AI 專用通道沒有模型黑名單，信任 config.yaml 設定
    BLACKLISTED_MODELS: set[str] = set()
else:
    # 原始 AI Studio 專屬路由與優先序
    MODELS_BY_PRIORITY: list[str] = [
        "gemini-2.5-flash",           # ★★★ 首選：最新一代主力 Flash，速度快且支援長文本
        "gemini-flash-latest",        # ★★  別名，通常會導向最新版的 Flash
        "gemini-3.5-flash",           # ★★  保留舊設定以防萬一
        "gemini-3-flash-preview",     # ★★  備援一
        "gemini-3.1-flash-lite",      # ★   輕量備援
        "gemini-flash-lite-latest",   # ★   輕量備援別名
    ]

    # 永久禁止清單（limit:0 或確認無配額）
    BLACKLISTED_MODELS: set[str] = {
        "gemini-2.0-flash",       # limit:0 永久封鎖
        "gemini-2.0-flash-lite",
        "gemini-2.5-pro",         # 免費池通常無 Pro 權限，保留給 Vertex
        "gemini-3-pro-preview",
        "gemini-3.1-pro-preview",
        "gemini-pro-latest",
    }
    
    # 【隱藏版解封】：若使用者明確在設定檔中指名 gemini-2.5-pro，則解除封印
    if _high == "gemini-2.5-pro":
        BLACKLISTED_MODELS.discard("gemini-2.5-pro")
        if "gemini-2.5-pro" not in MODELS_BY_PRIORITY:
            MODELS_BY_PRIORITY.insert(0, "gemini-2.5-pro")

# 冷卻時間（秒）
COOLDOWN = {
    "429_RL":   120,    # 429 暫時限速
    "429_ZERO": 86400,  # 429 limit:0（永久無配額）
    "503":      60,     # 503 模型忙碌
    "404":      86400,  # 404 不存在
    "OTHER":    30,     # 未知錯誤
}

# 選模型技能陣列【重要》
# acquire() 用「品質優先】：由優先序主導，API 成功率只用來賴除積極破掉的模型
# 原因：成功率只代表「 API 呼叫沒有拋錯誤」，不代表轉譯品質
# gemini-3.1-flash-lite 不常出 API 錯誤 ≠ 法律專有名詞辨識正確
MIN_SUCCESS_RATE_TO_PREFER = 0.50   # 低於 50% 才降級，其他情況一律依品質優先序

STATE_PATH = r"C:\LocalAI_Workstation\config\model_router_state.json"


# ─────────────────────────────────────────────────────────────────
@dataclass
class ModelState:
    name: str
    failure_count: int = 0          # 連續失敗次數（成功後清零）
    cooldown_until: float = 0.0
    last_error: str = ""
    total_successes: int = 0
    total_failures: int = 0

    def is_available(self) -> bool:
        return time.time() >= self.cooldown_until

    def remaining_cooldown(self) -> float:
        return max(0.0, self.cooldown_until - time.time())

    @property
    def success_rate(self) -> float:
        total = self.total_successes + self.total_failures
        return self.total_successes / total if total > 0 else 1.0


# ─────────────────────────────────────────────────────────────────
class ModelRouter:
    """
    執行緒安全的 Gemini 模型路由代理。
    建議單例使用：get_router() 取得進程級實例。
    """

    def __init__(self, state_path: str = STATE_PATH):
        self._lock = threading.Lock()
        self._state_path = state_path
        self._models: dict[str, ModelState] = {}
        self._priority: list[str] = [m for m in MODELS_BY_PRIORITY
                                      if m not in BLACKLISTED_MODELS]
        self._load_state()
        for m in self._priority:
            if m not in self._models:
                self._models[m] = ModelState(name=m)

    # ── 公開 API ─────────────────────────────────────────────────

    def acquire(self) -> str:
        """
        回傳目前最佳可用模型。

        選模型邏輯（品質優先）：
          1. 依優先序看，找第一個「可用」且「成功率≥ MIN_SUCCESS_RATE_TO_PREFER」的
          2. 若所有可用模型都低於門滝，取成功率最高的那個
          3. 若全部冷卻中，選剩餘冷卻最短的

        【設計原則】優先序代表要求品質：
          gemini-3.5-flash 前沖級 > gemini-3-flash-preview > gemini-3.1-flash-lite 輕量備援
          成功率只用於賴除「積極破掉的」模型 (< 20%)
        """
        with self._lock:
            available = [
                m for m in self._priority
                if self._models[m].is_available()
            ]
            if not available:
                # 全部冷卻中 → 選剩餘冷卻最短的
                best = min(self._priority,
                           key=lambda m: self._models[m].cooldown_until)
                remaining = self._models[best].remaining_cooldown()
                logger.warning(
                    f"[ModelRouter] [WARN] 所有模型冷卻中！最快恢復: {best}"
                    f"（{remaining:.0f}s 後）"
                )
                return best

            # 【主要邏輯】依優先序找第一個成功率合格的模型
            for m in available:   # 已依 MODELS_BY_PRIORITY 排好
                st = self._models[m]
                total = st.total_successes + st.total_failures
                # 尚未使用過，或成功率≥ 門滝 → 可用
                if total == 0 or st.success_rate >= MIN_SUCCESS_RATE_TO_PREFER:
                    logger.debug(
                        f"[ModelRouter] 選用: {m} "
                        f"(成功率={st.success_rate:.0%}, 優先位#{self._priority.index(m)+1})"
                    )
                    return m

            # 所有可用模型都失敗率過高 → fallback 選成功率最高
            chosen = max(available, key=lambda m: self._models[m].success_rate)
            logger.warning(f"[ModelRouter] 所有模型失敗率 > {1-MIN_SUCCESS_RATE_TO_PREFER:.0%}，選 {chosen} (成功率最高)")
            return chosen

    def report_success(self, model: str) -> None:
        """通報成功，清零連續失敗計數。"""
        with self._lock:
            st = self._ensure(model)
            st.failure_count = 0
            st.cooldown_until = 0.0
            st.last_error = ""
            st.total_successes += 1
            snapshot = {n: asdict(s) for n, s in self._models.items()}
        # 釋鎖後才做檔案 I/O，防止持鎖期間善降效能
        self._save_state_data(snapshot)

    def report_error(self, model: str, exception: Exception) -> str:
        """
        通報錯誤，計算冷卻，回傳建議備援模型。
        Router 全權决策，呼叫者無需自行計算。
        """
        with self._lock:
            st = self._ensure(model)
            st.failure_count += 1
            st.total_failures += 1
            err = str(exception)
            etype = self._classify(err)
            cooldown = self._calc_cooldown(etype, err, st.failure_count)
            st.cooldown_until = time.time() + cooldown
            st.last_error = err[:200]
            logger.warning(
                f"[ModelRouter] {model} → {etype} "
                f"冷卻 {cooldown:.0f}s（連續#{st.failure_count}，"
                f"成功率={st.success_rate:.0%}）"
            )
            next_m = self._next_available(exclude=model)
            snapshot = {n: asdict(s) for n, s in self._models.items()}
        # 釋鎖後才做 I/O
        self._save_state_data(snapshot)
        logger.info(f"[ModelRouter] 切換備援: {next_m}")
        return next_m

    def call_with_failover(
        self,
        fn: Callable[[str], str],
        max_retries: int = 3,
    ) -> str:
        """
        通用帶切換包裝器。
        fn(model_name) -> str：呼叫者提供一個接受模型名稱的函式。
        自動在失敗時換模型重試。
        """
        last_exc: Optional[Exception] = None
        tried: set[str] = set()
        for attempt in range(max_retries):
            model = self.acquire()   # acquire() 內部已持鎖，回傳安全的模型名
            # 若所有 acquire 挑選的都已試過，強制選下一個
            if model in tried:
                with self._lock:
                    candidates = [
                        m for m in self._priority
                        if m not in tried
                        and self._models.get(m, ModelState(name=m)).is_available()
                    ]
                if not candidates:
                    break
                model = candidates[0]
            tried.add(model)
            try:
                result = fn(model)
                self.report_success(model)
                return result
            except Exception as e:
                last_exc = e
                self.report_error(model, e)
                logger.warning(f"[ModelRouter] call_with_failover 第{attempt+1}次失敗 ({model})，換模型重試")
                time.sleep(1)
        raise last_exc or RuntimeError("所有模型均失敗")

    def status_report(self) -> str:
        """可讀狀態摘要。"""
        lines = ["[ModelRouter] 模型狀態報告:"]
        with self._lock:
            for m in self._priority:
                st = self._models.get(m, ModelState(name=m))
                rate = f"成功率={st.success_rate:.0%}" if (st.total_successes + st.total_failures) > 0 else "未使用"
                if st.is_available():
                    status = f"✅ 可用  ({rate}, 成功={st.total_successes}, 失敗={st.total_failures})"
                else:
                    status = (f"⏳ 冷卻 {st.remaining_cooldown():.0f}s "
                              f"({rate}) [{st.last_error[:40]}]")
                lines.append(f"  {m:<35} {status}")
        return "\n".join(lines)

    def reset_model(self, model: str) -> None:
        with self._lock:
            if model in self._models:
                self._models[model].cooldown_until = 0.0
                self._models[model].failure_count = 0
                logger.info(f"[ModelRouter] 手動重置 {model}")
            self._save_state()

    def reset_all(self) -> None:
        with self._lock:
            for st in self._models.values():
                st.cooldown_until = 0.0
                st.failure_count = 0
            logger.info("[ModelRouter] 重置所有模型冷卻")
            self._save_state()

    def best_model(self) -> str:
        """回傳首選模型名稱（不論是否在冷卻）。"""
        return self._priority[0] if self._priority else "gemini-3.5-flash"

    # ── 私有方法 ─────────────────────────────────────────────────

    def _ensure(self, model: str) -> ModelState:
        if model not in self._models:
            self._models[model] = ModelState(name=model)
        return self._models[model]

    def _classify(self, err_msg: str) -> str:
        em = err_msg.lower()
        if "429" in err_msg or "resource_exhausted" in em or "resourceexhausted" in em:
            return "429_ZERO" if ("limit: 0" in err_msg or "quota_exceeded" in em) else "429_RL"
        if "503" in err_msg or "service_unavailable" in em:
            return "503"
        if "404" in err_msg or "not_found" in em or "model not found" in em:
            return "404"
        return "OTHER"

    def _calc_cooldown(self, etype: str, err_msg: str,
                       failure_count: int) -> float:
        base = COOLDOWN.get(etype, COOLDOWN["OTHER"])
        if etype in ("429_ZERO", "404"):
            return base  # 固定長冷卻

        # 嘗試從 API 回應中提取建議等待時間
        retry_delay = self._extract_retry_delay(err_msg)
        if retry_delay > 0:
            base = retry_delay

        # 指數退避（上限 10 分鐘）
        return min(base * (1.5 ** (failure_count - 1)), 600)

    @staticmethod
    def _extract_retry_delay(err_msg: str) -> float:
        for pattern in [
            r"retryDelay.*?['\"](\d+)s",
            r"retry in (\d+(?:\.\d+)?)\s*s",
            r"Please retry in (\d+(?:\.\d+)?)s",
        ]:
            m = re.search(pattern, err_msg, re.IGNORECASE)
            if m:
                return float(m.group(1))
        return 0.0

    def _next_available(self, exclude: str = "") -> str:
        candidates = [m for m in self._priority if m != exclude]
        avail = [m for m in candidates if self._models.get(m, ModelState(name=m)).is_available()]
        if avail:
            return avail[0]
        return min(candidates,
                   key=lambda m: self._models.get(m, ModelState(name=m)).cooldown_until,
                   default=self._priority[0])

    def _load_state(self) -> None:
        """Safety: 逐欄位載入，忽略不認識的旇欄位（防止版本讨和導致 TypeError crash）"""
        try:
            if os.path.exists(self._state_path):
                with open(self._state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                known_fields = {"name", "failure_count", "cooldown_until",
                                "last_error", "total_successes", "total_failures"}
                for name, d in data.items():
                    if name not in BLACKLISTED_MODELS:
                        safe_d = {k: v for k, v in d.items() if k in known_fields}
                        safe_d["name"] = name   # 確保 name 存在
                        self._models[name] = ModelState(**safe_d)
        except Exception as e:
            logger.warning(f"[ModelRouter] 無法載入狀態: {e}")

    def _save_state(self) -> None:
        """在鎖內呼叫：只收集 snapshot 資料（不做 I/O）。
        實際寫檔由 _save_state_data() 在鎖外完成。
        此方法保留以供 reset_model / reset_all 使用（這兩個不需要高頻呼叫）。
        """
        snapshot = {n: asdict(s) for n, s in self._models.items()}
        self._save_state_data(snapshot)

    def _save_state_data(self, snapshot: dict) -> None:
        """在鎖外執行實際檔案 I/O，防止持鎖 I/O 阻塞其他執行緒。"""
        try:
            os.makedirs(os.path.dirname(self._state_path), exist_ok=True)
            with open(self._state_path, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"[ModelRouter] 無法儲存狀態: {e}")


# ─────────────────────────────────────────────────────────────────
# 進程級單例
# ─────────────────────────────────────────────────────────────────
_router_instance: Optional[ModelRouter] = None
_router_lock = threading.Lock()


def get_router() -> ModelRouter:
    global _router_instance
    if _router_instance is None:
        with _router_lock:
            if _router_instance is None:
                _router_instance = ModelRouter()
    return _router_instance


# ─────────────────────────────────────────────────────────────────
# REST API 通用包裝器（供 multimodal_input.py / visual_analyzer.py）
# ─────────────────────────────────────────────────────────────────
def rest_generate(file_uri: str, mime_type: str, prompt: str,
                  api_key: str, max_retries: int = 3) -> str:
    """
    帶自動切換的 Gemini REST generateContent 呼叫。
    取代 multimodal_input.py 和 visual_analyzer.py 中的直連呼叫。
    有任何模型問題只需修改 model_router.py，不動其他腳本。
    """
    import requests

    def _call(model_name: str) -> str:
        url = (f"https://generativelanguage.googleapis.com"
               f"/v1beta/models/{model_name}:generateContent?key={api_key}")
        payload = {
            "contents": [{
                "parts": [
                    {"file_data": {"mime_type": mime_type, "file_uri": file_uri}},
                    {"text": prompt}
                ]
            }]
        }
        resp = requests.post(url, json=payload, timeout=120)
        if resp.status_code == 429:
            raise RuntimeError(f"429 RESOURCE_EXHAUSTED. {resp.text[:200]}")
        if resp.status_code == 503:
            raise RuntimeError(f"503 SERVICE_UNAVAILABLE. {resp.text[:200]}")
        if resp.status_code == 404:
            raise RuntimeError(f"404 NOT_FOUND. {resp.text[:200]}")
        if resp.status_code != 200:
            raise RuntimeError(f"Gemini REST error {resp.status_code}: {resp.text[:200]}")
        try:
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Unexpected response: {resp.json()}") from e

    return get_router().call_with_failover(_call, max_retries=max_retries)


# ─────────────────────────────────────────────────────────────────
# SDK 通用包裝器（供 visual_analyzer.py 透過 Bytes 傳送，支援 Vertex AI）
# ─────────────────────────────────────────────────────────────────
def sdk_generate_image(image_bytes: bytes, mime_type: str, prompt: str,
                       api_key: str, max_retries: int = 3, use_vertex: bool = False,
                       vertex_project: str = None, vertex_location: str = None, vertex_cred: str = None) -> str:
    """
    透過 google-genai SDK 將圖片 Bytes 傳送至 Vertex AI 或 AI Studio。
    取代 REST 繁瑣的上傳流程。
    """
    import google.genai as genai
    from google.genai import types
    import os

    def _call(model_name: str) -> str:
        if use_vertex:
            if vertex_cred:
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = vertex_cred
            client = genai.Client(vertexai=True, project=vertex_project, location=vertex_location)
        else:
            client = genai.Client(api_key=api_key)
            
        part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        resp = client.models.generate_content(
            model=model_name,
            contents=[prompt, part]
        )
        return resp.text

    return get_router().call_with_failover(_call, max_retries=max_retries)

# ─────────────────────────────────────────────────────────────────
# CLI 工具
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    router = ModelRouter()

    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "status":
        print(router.status_report())

    elif cmd == "reset":
        model = sys.argv[2] if len(sys.argv) > 2 else None
        if model:
            router.reset_model(model)
            print(f"✅ 已重置 {model}")
        else:
            router.reset_all()
            print("✅ 已重置所有模型")

    elif cmd == "test":
        sys.path.insert(0, r"C:\LocalAI_Workstation\scripts")
        from quota_manager import QuotaManager
        import google.genai as genai
        qm = QuotaManager()
        key = qm.keys[2] if len(qm.keys) > 2 else qm.keys[0]
        client = genai.Client(api_key=key)
        print(f"測試金鑰: {key[:16]}...")
        for m in router._priority:
            try:
                t0 = time.time()
                resp = client.models.generate_content(model=m, contents="Reply: OK")
                elapsed = time.time() - t0
                print(f"  ✅ {m:<35} {elapsed:.1f}s")
                router.report_success(m)
            except Exception as e:
                print(f"  ❌ {m:<35} {str(e)[:60]}")
                router.report_error(m, e)
            time.sleep(1)
        print()
        print(router.status_report())

    elif cmd == "best":
        print(router.best_model())

    else:
        print("用法:")
        print("  python model_router.py status       # 查看狀態")
        print("  python model_router.py reset        # 重置所有冷卻")
        print("  python model_router.py reset <model># 重置單一模型")
        print("  python model_router.py test         # 實際 API 測試")
        print("  python model_router.py best         # 顯示首選模型")
