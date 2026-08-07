# [CRITICAL CROSS-FILE DEPENDENCY WARNING]
# Upstream: LexMind_V6_沙盒驗證版.ps1
# Downstream: stt_runner.py, etc.
# Shared State: Database, Chunks
#
# [LexMind V6 Ironclad Compliance]
# - Rule 1/2 : 終端輸出禁 Emoji，僅限純 ASCII 圖示
# - Rule 3   : 本檔案以 UTF-8-SIG 儲存
# - Rule 4   : 讀檔一律 errors="replace"
# - Rule 5   : 字典取值一律 .get()
# - Rule 7   : 不在 import 階段執行 sys.stdout.reconfigure（pythonw / 10106 防護）
# - Rule 11  : JSON 寫入 ensure_ascii=True
# - Rule 13  : 僅就地修補，不建新檔、不改檔名、不改業務邏輯
#
# [V3 終極防線 (Peer Review 對位實裝)]
# - 漏洞 1: 金鑰只由「取得它的那條 Worker」在 finally 釋放（key_for_release 身分核對），
#           主執行緒絕不強制回收；as_completed 逾時僅記錄，不做金鑰手術。
# - 漏洞 2: 不信任 Windows 檔案時間戳（os.replace 會重置 getctime），
#           老化計算一律讀取 manifest payload 的 created_at；
#           atomic_json_dump 以 finally 清理 .tmp 殘骸。
# - 漏洞 3: 任務排序採半衰期漸進演算法 calculate_effective_priority()，
#           分數永不塌到 1.0 以下，科目優先序鐵律不崩壞。

import os
import sys
import time
import json
import math
import argparse
import threading
import subprocess
import random
import faulthandler
from pathlib import Path
from datetime import datetime as _dt, timedelta as _td, timezone as _tz
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError as FuturesTimeoutError

# 故障快照：啟用 faulthandler（Python 原生）以備用
try:
    faulthandler.enable()
except Exception:
    pass  # pythonw.exe 之下 sys.stderr 可能為 None，faulthandler.enable 會失敗

# 共用監控工具
_mu_dir = os.path.dirname(os.path.abspath(__file__))
try:
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("monitoring_utils", os.path.join(_mu_dir, "monitoring_utils.py"))
    _mu = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_mu)
    dump_stack_snapshot = _mu.dump_stack_snapshot
except Exception:
    def dump_stack_snapshot(**kwargs):
        pass  # fallback: no-op if monitoring_utils not available

ENTERPRISE_MODE = os.environ.get("LEXMIND_ENTERPRISE", "0") == "1"


def _safe_stderr_print(text):
    """pythonw.exe 之下 stderr 可能為 None；啟動期訊息寫不出去不得中止程序。"""
    try:
        if getattr(sys, "stderr", None) is not None:
            print(text, file=sys.stderr)
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════
# * GCP PROJECT BOOTSTRAP — 必須在所有 Vertex / STT / QuotaManager
#   初始化之前執行，確保 google.auth.default() 能解析到正確 project。
# ══════════════════════════════════════════════════════════════════
def _bootstrap_gcp_project() -> None:
    """
    從 config.yaml 的 api.vertexai_project 讀取 GCP project ID，
    並在 GOOGLE_CLOUD_PROJECT / GCLOUD_PROJECT 尚未設定時自動注入。
    這樣整個 process（run_workflow、worker thread、google.auth）
    都能看到同一個 project，消除 'No project ID could be determined' 警告。
    """
    # 如果兩個環境變數都已設定，不做任何事
    if os.environ.get("GOOGLE_CLOUD_PROJECT") and os.environ.get("GCLOUD_PROJECT"):
        return

    # config.yaml 以絕對路徑定位（與 quota_manager.py 同源）
    _workspace_root = Path(__file__).resolve().parent.parent   # C:\LocalAI_Workstation\
    config_path = _workspace_root / "config.yaml"
    if not config_path.exists():
        # 備援：scripts_v6 的父目錄就是 workspace root，嘗試當前腳本同層
        config_path = Path(__file__).resolve().parent / "config.yaml"

    vertexai_project = None
    if config_path.exists():
        try:
            import yaml as _yaml
            with open(config_path, "r", encoding="utf-8-sig", errors="replace") as _f:
                _cfg = _yaml.safe_load(_f)
            vertexai_project = ((_cfg or {}).get("api", {}) or {}).get("vertexai_project")
        except Exception as _e:
            # 啟動期讀取失敗不應中止程序，只記錄到 stderr
            _safe_stderr_print(f"[BOOTSTRAP] WARNING: 讀取 config.yaml 失敗: {_e}")

    if not vertexai_project:
        return  # config.yaml 無此欄位，讓 google.auth 自行處理

    if not os.environ.get("GOOGLE_CLOUD_PROJECT"):
        os.environ["GOOGLE_CLOUD_PROJECT"] = str(vertexai_project)
        _safe_stderr_print(f"[BOOTSTRAP] GOOGLE_CLOUD_PROJECT = {vertexai_project!r} (from config.yaml)")

    if not os.environ.get("GCLOUD_PROJECT"):
        os.environ["GCLOUD_PROJECT"] = str(vertexai_project)
        _safe_stderr_print(f"[BOOTSTRAP] GCLOUD_PROJECT = {vertexai_project!r} (from config.yaml)")


# 立即執行 —— 必須在所有其他 import 之前
_bootstrap_gcp_project()
# ══════════════════════════════════════════════════════════════════

# 將 scripts 目錄加入 PATH
script_dir = Path(__file__).parent.resolve()
if str(script_dir) not in sys.path:
    sys.path.append(str(script_dir))

from file_watcher import scan_new_files
from preprocess_media import preprocess
from chunk_planner import plan_chunks
from stt_runner import run_stt
from merge_transcript import merge_workflow
from markdown_formatter import format_markdown
from workflow_helper import (
    ensure_dirs, log_workflow, log_error, load_config,
    get_engine_setting, safe_reconfigure_stdio, log_stage,
)
from manifest_manager import ManifestManager, update_manifest

try:
    from scripts_v6.quota_manager import QuotaManager
except ImportError:
    from quota_manager import QuotaManager


# [Block D] 狀態收斂與效能優化 (原子寫入)
def atomic_json_dump(data, filepath):
    """
    [Rule 11] ensure_ascii=True
    [V3 漏洞 2] finally 清道夫：任何失敗路徑都不得留下 .tmp 殘骸。
    僅供「非 manifest」狀態檔（kpi_state 等）使用；
    task manifest 一律改走 ManifestManager / update_manifest。
    """
    filepath = str(filepath)
    tmp_path = f"{filepath}.{os.getpid()}.{threading.get_ident()}.tmp"
    replaced = False
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=True, indent=2)
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
        max_retries = 30
        for i in range(max_retries):
            try:
                os.replace(tmp_path, filepath)
                replaced = True
                return
            except PermissionError:
                if i == max_retries - 1:
                    log_error(f"嚴重 I/O 錯誤：等待 {max_retries} 次後仍無法覆寫 {filepath}")
                    raise
                sleep_time = (0.1 * (1.2 ** i)) + random.uniform(0.01, 0.05)
                time.sleep(min(sleep_time, 2.0))
    finally:
        # [V3 漏洞 2] .tmp 檔案清道夫
        if not replaced and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def _safe_json_read(filepath, default=None):
    """[Rule 4] utf-8-sig + errors='replace'，失敗回傳 default。"""
    try:
        if not os.path.exists(filepath):
            return default
        with open(filepath, "r", encoding="utf-8-sig", errors="replace") as f:
            return json.load(f)
    except Exception:
        return default


class SingleInstanceLock:
    def __init__(self, lock_file):
        self.lock_file = lock_file
        self.fp = None

    def acquire(self):
        try:
            self.fp = open(self.lock_file, 'a+')
            self.fp.seek(0)
            if sys.platform == 'win32':
                import msvcrt
                msvcrt.locking(self.fp.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except (IOError, OSError, ImportError):
            if self.fp:
                try:
                    self.fp.close()
                except Exception:
                    pass
            return False

    def release(self):
        if self.fp:
            try:
                self.fp.seek(0)
                if sys.platform == 'win32':
                    import msvcrt
                    msvcrt.locking(self.fp.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self.fp.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
            try:
                self.fp.close()
            except Exception:
                pass
            try:
                os.remove(self.lock_file)
            except Exception:
                pass


def get_legal_priority_score(source_name: str) -> int:
    """
    國考科目優先級評分（數字越小 = 越優先處理）

    排序邏輯（依台灣律師高考 / 地政士高考 / 司法特考核心科目）：
      10  → 憲法（根本大法）
      20  → 民法（最重要主科）
      25  → 刑法
      30  → 行政法（含行政程序法、國家賠償）
      40  → 程序法：民訴、刑訴、行訴、強執、家事
      50  → 土地法規：土地法、土地登記、地籍、地政
      60  → 商事法核心：公司法、票據法、保險法
      70  → 勞動、海商、仲裁等次要商事
      80  → 特別法：智財、消保、公平交易、個資等
      90  → 地政專業科目：不動產估價、都市計畫
      100 → 其他未分類
    """
    name = str(source_name or "").lower()

    # 10. 憲法（根本大法）
    if any(kw in name for kw in ["憲法", "憲政"]):
        return 10

    # 20. 民法（最重要主科）
    if "民法" in name:
        return 20

    # 25. 刑法
    if "刑法" in name:
        return 25

    # 30. 行政法（含行政程序法、國家賠償）
    if any(kw in name for kw in ["行政法", "行政程序", "國家賠償", "國賠"]):
        return 30

    # 40. 程序法
    if any(kw in name for kw in [
        "民事訴訟", "民訴", "刑事訴訟", "刑訴",
        "行政訴訟", "強制執行", "強執", "家事事件", "程序法"
    ]):
        return 40

    # 50. 土地法規核心（地政士高考主科）
    if any(kw in name for kw in [
        "土地法", "土地登記", "土登", "地籍測量", "地籍",
        "土地法規", "地政法規"
    ]):
        return 50

    # 60. 商事法核心（公司法 / 票據 / 保險 / 海商 / 證交法 / 稅法 同級）
    if any(kw in name for kw in [
        "公司法", "票據", "保險法", "海商",
        "證交法", "證券交易", "金融法", "銀行法", "期貨",
        "稅法", "稅捽", "稅務", "所得稅",
    ]):
        return 60

    # 70. 其他商事 / 勞動
    if any(kw in name for kw in ["勞動基準", "勞基", "勞動法", "仲裁", "信託法"]):
        return 70

    # 80. 特別法
    if any(kw in name for kw in [
        "專利", "著作權", "商標", "消費者保護", "消保",
        "公平交易", "營業秘密", "個人資料", "個資",
        "破產", "公寓大廈", "家庭暴力", "家暴"
    ]):
        return 80

    # 90. 地政輔助專業科目
    if any(kw in name for kw in ["不動產估價", "不動產評價", "都市計畫", "測量法"]):
        return 90

    # 100. 其他未分類
    return 100


def calculate_effective_priority(manifest_data: dict) -> float:
    """
    [V3 漏洞 3] 半衰期漸進演算法 (Asymptotic Decay)：
      effective_score = 1.0 + (base_score - 1.0) * math.exp(-0.1 * wait_hours)

    - 分數越小越優先；等待越久分數越漸進逼近 1.0（防餓死），
      但永不跌破 1.0，等待時間相同時科目相對順序永不逆轉。
    - [V3 漏洞 2] wait_hours 一律取自 manifest payload 的 created_at，
      絕不使用 os.path.getctime（os.replace 會令其「返老還童」）。
    """
    base_score = float(get_legal_priority_score(manifest_data.get("source_name", "")))
    created_at = manifest_data.get("created_at")

    created_ts = None
    if created_at is not None:
        try:
            created_ts = float(created_at)
        except (TypeError, ValueError):
            try:
                created_ts = time.mktime(time.strptime(str(created_at).strip(), "%Y-%m-%d %H:%M:%S"))
            except Exception:
                created_ts = None

    wait_hours = 0.0
    if created_ts is not None and created_ts > 0:
        wait_hours = max(0.0, (time.time() - created_ts) / 3600.0)

    try:
        return 1.0 + (base_score - 1.0) * math.exp(-0.1 * wait_hours)
    except Exception:
        return base_score


# ════════════════════════════════════════════════════════════
# 沙盒實測結論（2026-07-10）：
#   上行速度: 277.37 Mbps（Speedtest.net 官測）
#   下行速度: 182.88 Mbps  Ping: 6ms
#   每個 chunk: 22 MB
#
# Phase A - Preprocess (FFmpeg 音訊提取)：CPU 密集
#   5 workers → CPU 93%（邊界，沙盒實測）
#   3 workers → CPU 56%（安全）
#
# Phase B - STT (Gemini Files API upload + generate)：I/O 密集
#   實測資料：並發=10 + 清除死 key 後 → 23.5/hr，並發=28 → 0/hr（全 503）
# ════════════════════════════════════════════════════════════
# ── 並發數設定（實測邊界值，非理論值）────────────────────────────────
PREPROCESS_CONCURRENCY   = 3
STT_CONCURRENCY_MIN      = 4    # 最低保底
STT_CONCURRENCY_MAX      = 6    # 避免顯示卡過熱藍白當機下修上限
STT_CONCURRENCY_DEFAULT  = 6    # 無 KPI 資料時預設值下修
# KPI 目標（completed/hr）
KPI_TARGET               = 40
# 單輪 batch 等待上限（秒）：僅用於記錄與釋放主執行緒，絕不做金鑰手術
BATCH_WAIT_TIMEOUT_SEC   = 1800

# ── 503 雪崩狀態追蹤（模組層級全域，不需持久化）────────────────────────────
_avalanche_floor = None            # None 表示目前無雪崩；int 表示強制壓低並發到 N
_avalanche_last_503_ts = 0.0       # 最近一次 503 的 epoch timestamp


def detect_503_avalanche_floor():
    """
    讀取 chunk_errors.log 過去 3 分鐘的 503 錯誤數量。
    若 503 頻率超過閾值，回傳「資料驅動的安全地板並發數」；否則回傳 None。

    安全地板計算邏輯（實測資料驅動）：
      - 從 kpi_state.json 讀取「上一個成功輪次的並發數」
      - 地板 = max(上次成功並發 // 2, STT_CONCURRENCY_MIN)
      - 若無歷史資料，地板 = STT_CONCURRENCY_MIN

    觸發閾值：3 分鐘內出現 >= 5 個 503 錯誤
    """
    import re

    error_log = Path("A:/logs/chunk_errors.log")
    if not error_log.exists():
        return None

    cutoff = _dt.now(_tz.utc).replace(tzinfo=None) + _td(hours=8) - _td(minutes=3)
    count_503 = 0
    try:
        lines = error_log.read_text(encoding="utf-8", errors="replace").splitlines()[-200:]
        for line in lines:
            if "503" not in line and "UNAVAILABLE" not in line:
                continue
            m = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
            if m:
                try:
                    ts = _dt.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
                    if ts >= cutoff:
                        count_503 += 1
                except Exception:
                    pass
    except Exception:
        return None

    AVALANCHE_THRESHOLD = 5  # 3 分鐘 >= 5 個 503 才觸發
    if count_503 < AVALANCHE_THRESHOLD:
        return None  # 正常，無雪崩

    # 讀取上一個成功輪次的並發數（從 kpi_state）
    kpi_state_path = "A:/logs/kpi_state.json"
    last_good = STT_CONCURRENCY_DEFAULT
    state = _safe_json_read(kpi_state_path, default={}) or {}
    try:
        v = int(state.get("stt_concurrency", STT_CONCURRENCY_DEFAULT))
        if v > 0:
            last_good = v
    except (TypeError, ValueError):
        pass

    # 安全地板 = 上次並發的一半，但不低於 STT_CONCURRENCY_MIN
    floor = max(last_good // 2, STT_CONCURRENCY_MIN)
    log_workflow(
        f"[503-Avalanche] 偵測到 {count_503} 個 503（3min 內），"
        f"上次並發={last_good} -> 安全地板={floor}（實測資料驅動）"
    )
    return floor


def compute_adaptive_concurrency() -> int:
    """
    依最近 KPI 歷史動態決定 STT 並發數。
    規則（實測資料驅動，非時間硬編碼）：
      - KPI >= target*1.5 (60/hr)：並發充足，略降節省資源
      - KPI >= target (40/hr)：剛好達標，維持
      - KPI >= target*0.5 (20/hr)：差一點，+2
      - KPI > 0：明顯不足，+2
      - KPI = 0：視當前並發判斷是雪崩還是不足
      - KPI 資料不足 < 3 筆：用預設值
    """
    global _avalanche_floor, _avalanche_last_503_ts
    import re

    kpi_state_path = "A:/logs/kpi_state.json"

    # ── Step 0: 503 雪崩優先偵測（30 秒內立刻反應，最高優先）────────────────
    avalanche_floor = detect_503_avalanche_floor()
    if avalanche_floor is not None:
        # 進入雪崩模式：強制壓低並發，記錄時間戳
        _avalanche_floor = avalanche_floor
        _avalanche_last_503_ts = time.time()
        try:
            s = _safe_json_read(kpi_state_path, default={}) or {}
            s["stt_concurrency"] = _avalanche_floor
            s["avalanche_mode"] = True
            atomic_json_dump(s, kpi_state_path)
        except Exception:
            pass
        log_workflow(f"[503-Avalanche] 強制並發={_avalanche_floor}（安全地板，等待 API 恢復）")
        return _avalanche_floor
    elif _avalanche_floor is not None:
        # 雪崩已緩解：緩慢恢復（每輪 +1，最多到 STT_CONCURRENCY_MAX）
        elapsed = time.time() - _avalanche_last_503_ts
        if elapsed > 300:  # 5 分鐘無新 503 → 完全清除雪崩狀態
            log_workflow("[503-Avalanche] 5 分鐘無新 503，解除雪崩模式，恢復正常自適應")
            _avalanche_floor = None
        else:
            recovered = min(_avalanche_floor + 1, STT_CONCURRENCY_MAX)
            _avalanche_floor = recovered
            log_workflow(f"[503-Avalanche] 緩解中（{elapsed:.0f}s），並發緩慢恢復={recovered}")
            return recovered

    # ── Step 1: 正常 KPI 歷史回饋自適應（無雪崩時走此路）────────────────────
    kpi_vals = []

    # 1. 讀 kpi_state.json（最新一筆）
    state = _safe_json_read(kpi_state_path, default={}) or {}
    v = state.get("kpi_b1", None)
    if v is not None:
        try:
            kpi_vals.append(float(v))
        except (TypeError, ValueError):
            pass

    # 2. 讀 kpi_monitor.log 最近 30 分鐘的 KPI-B1 樣本
    kpi_log_path = "A:/logs/kpi_monitor.log"
    if os.path.exists(kpi_log_path):
        try:
            cutoff = _dt.now(_tz.utc) - _td(minutes=30)
            with open(kpi_log_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()[-120:]
            for l in lines:
                m = re.search(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\].*KPI-B1: ([\d.]+)", l)
                if m:
                    try:
                        ts = _dt.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
                        if ts > cutoff.replace(tzinfo=None):
                            kpi_vals.append(float(m.group(2)))
                    except Exception:
                        pass
        except Exception:
            pass

    # 3. 樣本不足：用預設值
    if len(kpi_vals) < 3:
        return STT_CONCURRENCY_DEFAULT

    # 4. 取近期平均（排除極端離群）
    kpi_vals.sort()
    trimmed = kpi_vals[len(kpi_vals)//5: -len(kpi_vals)//5 or None] or kpi_vals
    recent_kpi = sum(trimmed) / len(trimmed)

    # 5. 讀目前正在使用的並發數（上一輪設定值，存在 kpi_state）
    try:
        current = int(state.get("stt_concurrency", STT_CONCURRENCY_DEFAULT))
    except (TypeError, ValueError):
        current = STT_CONCURRENCY_DEFAULT

    # 6. KPI 回饋規則（含「並發過高反而更差」偵測）
    if recent_kpi >= KPI_TARGET * 1.5:
        new = max(current - 2, STT_CONCURRENCY_MIN)
        reason = f"KPI {recent_kpi:.1f} >= 60，充裕，略降並發"
    elif recent_kpi >= KPI_TARGET:
        new = current
        reason = f"KPI {recent_kpi:.1f} >= 40，達標，維持 {current}"
    elif recent_kpi >= KPI_TARGET * 0.5:
        new = min(current + 2, STT_CONCURRENCY_MAX)
        reason = f"KPI {recent_kpi:.1f} 20~40，不足，+2"
    elif recent_kpi > 0:
        new = min(current + 2, STT_CONCURRENCY_MAX)
        reason = f"KPI {recent_kpi:.1f} 0~20，明顯不足，+2"
    else:
        # KPI = 0：「可能是並發過高造成雪崩」vs「並發不夠」
        if current >= 12:
            new = max(current - 4, STT_CONCURRENCY_MIN)
            reason = f"KPI=0 且並發={current}>=12，疑似 API 雪崩，降並發 -4"
        else:
            new = min(current + 2, STT_CONCURRENCY_MAX)
            reason = f"KPI=0 且並發={current}<12，適度增加 +2"

    # 7. 回寫並發數到 kpi_state 供下一輪讀取
    try:
        s = _safe_json_read(kpi_state_path, default={}) or {}
        s["stt_concurrency"] = new
        s["avalanche_mode"] = False
        atomic_json_dump(s, kpi_state_path)
    except Exception:
        pass

    log_workflow(f"[AdaptiveConcurrency] {reason} -> 並發={new}（樣本={len(kpi_vals)}, 近期KPI均值={recent_kpi:.1f}）")
    return new


import re  # detect_503_avalanche_floor / compute_adaptive_concurrency 共用

TASK_CONCURRENCY = STT_CONCURRENCY_DEFAULT  # 初始值，會被 compute_adaptive_concurrency() 覆蓋


def _safe_mark_task_failed(manifest_path, error_text: str) -> None:
    """
    [狀態機防護] 寫 failed 前必須在鎖內重新讀取當前 manifest：
      - 若已被 stt_runner 回退為 chunked / stt=pending，不得覆寫為 failed；
      - 若 merge 已寫成 merged、formatter 已寫成 completed，不得用舊異常覆寫；
      - 記錄 error 時不得刪除 paths、steps、degraded_reason、merge_mode、needs_review 等欄位。
    """
    result_box = {"skipped": None}

    def _apply(m):
        status = str(m.get("status", ""))
        steps = m.get("steps", {}) or {}

        if status == "chunked" and steps.get("stt") == "pending":
            result_box["skipped"] = "already reset to chunked/pending by stt_runner"
            return
        if status in ("merged", "completed"):
            result_box["skipped"] = f"already advanced to {status}"
            return
        if status.startswith("failed_validation"):
            result_box["skipped"] = f"keep validation state {status}"
            return

        m["status"] = "failed"
        m["error"] = str(error_text)[:2000]

    ok = update_manifest(manifest_path, _apply)
    if not ok:
        log_error(f"Failed to mark task as failed safely: {manifest_path}")
    elif result_box.get("skipped"):
        log_workflow(f"Workflow Engine: skip failed overwrite ({result_box.get('skipped')}) -> {manifest_path}")


def run_single_task_safe(manifest: dict, manifest_path, exclusive_key, qm, chunking_only: bool) -> bool:
    """
    包裝單一任務的完整流程，供 ThreadPoolExecutor 並列呼叫。
    exclusive_key 可為 None，此時在 Worker 啟動時才向 qm 按需取得，
    確保 key 不被預先鎖死在等待佇列中。

    [V3 漏洞 1] 金鑰生命週期鐵律：
      - 只有「本執行緒自己取得」的金鑰，才由本執行緒在 finally 釋放；
      - 釋放時核對 key_for_release（取得當下的局部變數），
        絕不讀取任何共享變數，殭屍執行緒甦醒也無法釋放到別人的金鑰；
      - 主執行緒（process_active_tasks）絕不強制回收任何金鑰。
    返回 True 表示任務成功。
    """
    # ── 避免多個 Worker 在同一毫秒打向 API，給予 1~4 秒隨機緩衝 ──
    time.sleep(random.uniform(1.0, 4.0))
    paths = ensure_dirs()
    task_id = manifest.get("task_id", "unknown_task")

    key_acquired_here = False
    key_for_release = None   # [V3] 身分核對：只釋放這個值，永不讀共享狀態

    # ── 按需取得 key（若呼叫方沒有預先分配）──
    if not chunking_only and exclusive_key is None and qm is not None:
        try:
            acquired = qm.acquire_key_exclusive()
            key_acquired_here = True
            if acquired == "__VERTEX_AUTH__":
                # Vertex 模式：哨兵不是真實 key，下游改走 ADC 路徑
                log_workflow(f"[Parallel Dispatcher] Task {task_id} 開始（Vertex AI 模式）")
                exclusive_key = None
                key_for_release = None   # 哨兵不進入釋放流程
            else:
                exclusive_key = acquired
                key_for_release = acquired
                log_workflow(f"[Parallel Dispatcher] Task {task_id} 開始，按需取得金鑰: {str(acquired)[:8]}...")
        except RuntimeError:
            log_error(f"[Parallel Dispatcher] Task {task_id} 無可用金鑰，跳過本輪。")
            return False
    elif exclusive_key == "__VERTEX_AUTH__":
        log_workflow(f"[Parallel Dispatcher] Task {task_id} 開始（Vertex AI 模式，傳入哨兵）")
        exclusive_key = None
    elif exclusive_key:
        # 呼叫方預先分配的 key：由呼叫方負責釋放，本函式不碰
        log_workflow(f"[Parallel Dispatcher] Task {task_id} 開始，使用傳入金鑰: {str(exclusive_key)[:8]}...")
    else:
        log_workflow(f"[Parallel Dispatcher] Task {task_id} 開始（chunking-only 模式）")

    # ── 接入點 1: run_single_task_safe 入口 ───────────────────────────────
    _task_start_time = time.time()
    source_name = manifest.get("source_name", "unknown")
    chunk_count = manifest.get("chunk_count", 0)
    # [斷點] 任務層 IN：卡住的任務 = 有 IN 無 OUT，一條指令定位
    log_stage(task_id, "task", "IN", extra={"source": source_name, "status": manifest.get("status", "")})
    try:
        _task_ok = _run_task_steps(manifest, manifest_path, paths, exclusive_key, chunking_only)
        log_stage(task_id, "task", "OUT", ok=_task_ok, elapsed=time.time() - _task_start_time)
        return _task_ok
    except Exception as e:
        _elapsed = time.time() - _task_start_time
        # 堆疊快照（接入點 1）
        dump_stack_snapshot(
            task_id=task_id,
            source_name=source_name,
            stage="run_single_task_safe",
            chunk_count=chunk_count,
            elapsed_seconds=_elapsed,
        )
        log_error(f"[Parallel Dispatcher] Task {task_id} 發生異常：{e}")
        log_stage(task_id, "task", "OUT", ok=False, elapsed=_elapsed, extra={"error": str(e)[:100]})
        _safe_mark_task_failed(manifest_path, str(e))
        return False
    finally:
        # [V3 漏洞 1] 只有本函式自己取的真實 key 才在這裡釋放，且只釋放 key_for_release
        if key_acquired_here and qm is not None and key_for_release:
            try:
                qm.release_key(key_for_release)
            except Exception as release_err:
                log_error(f"[Parallel Dispatcher] Task {task_id} 釋放金鑰失敗：{release_err}")


def _read_manifest_locked(manifest_path):
    """在鎖內重新讀取最新 manifest，避免用舊記憶體資料覆蓋他人寫入。"""
    with ManifestManager(manifest_path) as mm:
        data = mm.read()
    return data if isinstance(data, dict) else {}


def _run_task_steps(manifest: dict, manifest_path, paths: dict, exclusive_key, chunking_only: bool) -> bool:
    """
    執行單一任務的工作流步驟。
    全程同步執行 stt→merge→formatter。
    exclusive_key: 多工模式下此 Task 獨佔的 API 金鑰，傳遞給 run_stt()。
    返回 True 表示任務成功完成。
    """
    task_id = manifest.get("task_id", "unknown")
    source_name = manifest.get("source_name")
    steps = manifest.get("steps")

    # [FIX] 計時變數必須在任何步驟之前初始化，
    # 否則 preprocess/chunk_planner 階段拋例外時 except 區塊會 NameError
    _steps_start = time.time()
    _source = manifest.get("source_name", "unknown")
    _chunks = manifest.get("chunk_count", 0)

    if not source_name:
        log_error(f"Workflow Engine: task {task_id} missing source_name, mark for review")
        def _mark_review(m):
            m["status"] = "needs_review"
        update_manifest(manifest_path, _mark_review)
        return False

    if steps is None:
        log_error(f"Workflow Engine: task {task_id} missing steps, mark for review")
        def _mark_review(m):
            m["status"] = "needs_review"
        update_manifest(manifest_path, _mark_review)
        return False

    # ── 相容墊片：舊格式 manifest 用 video_path，新格式用 source_path ──
    if "source_path" not in manifest and "video_path" in manifest:
        def _compat_path(m):
            if "source_path" not in m and "video_path" in m:
                m["source_path"] = m.get("video_path", "")
        update_manifest(manifest_path, _compat_path)
        manifest = _read_manifest_locked(manifest_path) or manifest

    # ── 真實任務步驟 ──
    try:
        # 步驟二：Preprocess
        if (manifest.get("steps", {}) or {}).get("preprocess") == "pending":
            log_stage(task_id, "preprocess", "IN")
            _t0 = time.time()
            success = preprocess(task_id)
            log_stage(task_id, "preprocess", "OUT", ok=bool(success), elapsed=time.time() - _t0)
            if not success:
                raise RuntimeError("Preprocess step failed")
            manifest = _read_manifest_locked(manifest_path)

        # 步驟三：Chunk Planner
        if (manifest.get("steps", {}) or {}).get("chunk_planner") == "pending":
            log_stage(task_id, "chunk_planner", "IN")
            _t0 = time.time()
            success = plan_chunks(task_id)
            log_stage(task_id, "chunk_planner", "OUT", ok=bool(success), elapsed=time.time() - _t0)
            if not success:
                raise RuntimeError("Chunk planning step failed")
            manifest = _read_manifest_locked(manifest_path)

        if chunking_only:
            log_workflow(f"Workflow Engine: Task {task_id} chunking done. Stopping (--chunking-only mode).")
            return True

        # ── 任務計時（用於接入點 2/3/4 的 elapsed_seconds）────────────────────
        _steps_start = time.time()
        _source = manifest.get("source_name", "unknown")
        _chunks = manifest.get("chunk_count", 0)

        # 步驟四：STT（傳入排他金鑰供並列模式使用）
        if (manifest.get("steps", {}) or {}).get("stt") == "pending":
            _stt_start = time.time()
            log_stage(task_id, "stt", "IN", extra={"chunks": _chunks})
            success = run_stt(task_id, exclusive_key=exclusive_key)
            log_stage(task_id, "stt", "OUT", ok=bool(success), elapsed=time.time() - _stt_start)
            if not success:
                # ── 接入點 2: STT 失敗堆疊快照 ───────────────────────
                dump_stack_snapshot(
                    task_id=task_id,
                    source_name=_source,
                    stage="stt",
                    chunk_count=_chunks,
                    elapsed_seconds=time.time() - _stt_start,
                )
                raise RuntimeError("STT transcription step failed")
            manifest = _read_manifest_locked(manifest_path)

        # 步驟五：Merge
        if (manifest.get("steps", {}) or {}).get("merge") == "pending":
            _merge_start = time.time()
            log_stage(task_id, "merge", "IN", extra={"chunks": _chunks})
            success = merge_workflow(task_id)
            log_stage(task_id, "merge", "OUT", ok=bool(success), elapsed=time.time() - _merge_start)
            if not success:
                # ── 接入點 3: merge_map / reduce 失敗堆疊快照 ─────────────
                dump_stack_snapshot(
                    task_id=task_id,
                    source_name=_source,
                    stage="merge_map_reduce",
                    chunk_count=_chunks,
                    elapsed_seconds=time.time() - _merge_start,
                )
                raise RuntimeError("Merge step failed")
            manifest = _read_manifest_locked(manifest_path)

        # 步驟六：Formatter
        if (manifest.get("steps", {}) or {}).get("formatter", "pending") == "pending":
            log_stage(task_id, "formatter", "IN")
            _t0 = time.time()
            success = format_markdown(task_id)
            log_stage(task_id, "formatter", "OUT", ok=bool(success), elapsed=time.time() - _t0)
            if not success:
                raise RuntimeError("Formatter step failed")
            manifest = _read_manifest_locked(manifest_path)

        # 任務完成收斂：
        # [狀態機防護] 在鎖內重讀後才收斂為 completed；
        # formatter 的 failed_validation_* 狀態必須保留，不得覆寫；
        # 不得刪除 paths / degraded_reason / merge_mode / needs_review 等欄位。
        def _mark_completed(m):
            status = str(m.get("status", ""))
            if status.startswith("failed_validation"):
                return  # 保留驗收失敗狀態
            m["status"] = "completed"
        update_manifest(manifest_path, _mark_completed)
        log_workflow(f"Workflow Engine: Task {task_id} completed successfully!")

        return True

    except Exception as e:
        _total_elapsed = time.time() - _steps_start
        # ── 接入點 4: Vertex / 外部 API 呼叫層經常是此類病例的根源─────────────
        dump_stack_snapshot(
            task_id=task_id,
            source_name=_source,
            stage="vertex_or_external_api",
            chunk_count=_chunks,
            elapsed_seconds=_total_elapsed,
        )
        log_error(f"Workflow Engine: Critical error in task {task_id}: {e}")
        _safe_mark_task_failed(manifest_path, str(e))
        return False


def process_active_tasks(chunking_only=False):
    paths = ensure_dirs()
    manifests_dir = paths.get("manifests_dir")

    # ── 掃描 active manifests（[Rule 4/5] 安全讀取）──
    active_tasks = []
    for p in Path(manifests_dir).glob("*.json"):
        if not p.name.startswith("task_") or p.name.endswith("_chunks.json"):
            continue
        try:
            with open(p, "r", encoding="utf-8-sig", errors="replace") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                continue

            status = str(data.get("status", ""))

            # 終止狀態不得重新進入 active batch
            if status in ("completed", "failed", "needs_review", "hold") or status.startswith("failed_validation"):
                continue

            # chunking_only 模式：chunk_planner 已完成者跳過
            if chunking_only and (data.get("steps", {}) or {}).get("chunk_planner") == "completed":
                continue

            # [V3 漏洞 2] created_at 補寫進 payload（只補一次），
            # 老化演算法永不依賴 Windows 檔案時間戳
            if not data.get("created_at"):
                def _backfill_created(m):
                    if not m.get("created_at"):
                        m["created_at"] = time.time()
                update_manifest(p, _backfill_created)
                data["created_at"] = data.get("created_at") or time.time()

            active_tasks.append((p, data))
        except Exception:
            pass

    # ── [V3 漏洞 3] 半衰期漸進老化排序：分數小者優先，科目鐵律不崩壞 ──
    active_tasks.sort(key=lambda x: (
        calculate_effective_priority(x[1]),
        x[1].get("task_id", "")
    ))

    if not active_tasks:
        return

    log_workflow(f"Workflow Engine: Found {len(active_tasks)} active tasks to process.")

    # ── [統一配置讀取層] 一律經 get_engine_setting 讀引擎，消除層級誤判 ──
    sys_config = load_config()
    stt_engine = str(get_engine_setting(sys_config, "stt_engine", "gemini")).lower()
    merge_engine = str(get_engine_setting(sys_config, "merge_engine", "gemini")).lower()

    if stt_engine == "vertexai" and merge_engine == "vertexai":
        log_workflow("[INFO] 系統走企業高速公路 (Vertex-only)，跳過 QuotaManager 私家金鑰盤查")
        qm = None
    else:
        try:
            qm = QuotaManager()
        except Exception as qm_err:
            log_error(f"QuotaManager 初始化失敗，回退至無共享金鑰模式：{qm_err}")
            qm = None

    # ── 嚴格分相位調度：每輪只選一種任務類別，並發額度絕不混用 ──
    #   Phase B (STT/merge/formatter)：chunked / transcribed / merged 及其他中途狀態
    #   Phase A (Preprocess)         ：queued
    queued_tasks  = [(p, d) for p, d in active_tasks if d.get("status") == "queued"]
    chunked_tasks = [(p, d) for p, d in active_tasks if d.get("status") != "queued"]

    if chunking_only:
        batch_source = queued_tasks if queued_tasks else chunked_tasks
        effective_concurrency = PREPROCESS_CONCURRENCY
        log_workflow(
            f"[Dispatcher] Chunking-only：本輪 {len(batch_source)} 個任務 -> 並發={effective_concurrency}（CPU 安全）"
        )
    elif chunked_tasks:
        # b. 若有 chunked（或其他中途態），優先且只處理這一類
        batch_source = chunked_tasks
        effective_concurrency = compute_adaptive_concurrency()
        log_workflow(
            f"[Dispatcher] [OK] STT Phase B：本輪只處理 {len(chunked_tasks)} 個 chunked/中途任務"
            f"（{len(queued_tasks)} 個 queued 留待下一輪）-> 並發={effective_concurrency}（KPI自適應）"
        )
    else:
        # 否則處理 queued，使用 PREPROCESS_CONCURRENCY，杜絕 queued 蹭 STT 高並發
        batch_source = queued_tasks
        effective_concurrency = PREPROCESS_CONCURRENCY
        log_workflow(
            f"[Dispatcher] Preprocess Phase A：本輪只處理 {len(queued_tasks)} 個 queued 任務"
            f" -> 並發={effective_concurrency}（CPU 安全）"
        )

    batch = batch_source[:effective_concurrency * 8]
    log_workflow(f"[Parallel Dispatcher] 本輪提交 {len(batch)}/{len(active_tasks)} 個任務（並發數 {effective_concurrency}）")

    with ThreadPoolExecutor(max_workers=effective_concurrency) as executor:
        futures = {}
        for manifest_path, manifest in batch:
            fut = executor.submit(
                run_single_task_safe,
                manifest,
                manifest_path,
                None,   # 不預傳 key，Worker 自行按需取得
                qm,
                chunking_only,
            )
            futures[fut] = manifest.get("task_id", "unknown_task")

        # [V3 漏洞 1] as_completed 加上逾時，但逾時「僅記錄與放行主執行緒」，
        # 絕不強制回收任何 Worker 的金鑰；Worker 端 API 呼叫已有硬性逾時，
        # 執行緒必然在有界時間內自行結束並在自己的 finally 釋放金鑰。
        pending_ids = set(futures.values())
        try:
            for future in as_completed(futures, timeout=BATCH_WAIT_TIMEOUT_SEC):
                task_id = futures.get(future, "unknown_task")
                pending_ids.discard(task_id)
                try:
                    success = future.result()
                    status = "success" if success else "failed"
                    log_workflow(f"[Parallel Dispatcher] Task {task_id} 完成，狀態：{status}")
                except Exception as e:
                    log_error(f"[Parallel Dispatcher] Task {task_id} Future 異常：{e}")
        except FuturesTimeoutError:
            log_error(
                f"[Parallel Dispatcher] 本輪等待逾時（{BATCH_WAIT_TIMEOUT_SEC}s），"
                f"尚未回報的任務：{sorted(pending_ids)}；"
                f"不做金鑰回收，交由 Worker 端硬性逾時自行收斂。"
            )
        # 離開 with 區塊時 executor.shutdown(wait=True)：
        # Worker 端所有外部呼叫皆有硬性逾時，等待時間有上界，不會無聲卡死。

    # 若本輪還有剩餘任務，交由 run_loop 下一輪迭代處理（不遞迴，避免爆棧）
    remaining = len(active_tasks) - len(batch)
    if remaining > 0:
        log_workflow(f"[Parallel Dispatcher] 本輪完成，剩餘 {remaining} 個任務等待下一輪。")


def run_loop(chunking_only=False):
    log_workflow("臺灣法律教材長影音切片處理工作流監控服務已啟動！" + (" [僅切片模式]" if chunking_only else ""))
    ensure_dirs()

    while True:
        try:
            # 1. 掃描新檔案
            scan_new_files()
            # 2. 執行活動中任務（STT 完成後 Worker 立即釋放，merge/fmt 由 Daemon 接手）
            process_active_tasks(chunking_only)
        except RuntimeError as e:
            # 金鑰池全滅（所有 key 都 429）→ 等冷卻期結束
            err_lower = str(e).lower()
            if "exhausted" in err_lower or "all api keys" in err_lower:
                log_workflow(f"[Quota Cooldown] 金鑰池耗盡，進入 600 秒冷卻睡眠... ({e})")
                time.sleep(600)
                # 重置 key pool state
                try:
                    atomic_json_dump({"exhausted_keys": []}, "config/quota_state.json")
                    log_workflow("[Quota Cooldown] 金鑰池已重置，繼續排程。")
                except Exception:
                    pass
            else:
                log_error(f"Error in main workflow loop: {e}")
        except Exception as e:
            import traceback
            tb_flat = traceback.format_exc().replace("\r\n", " | ").replace("\n", " | ")
            log_error(f"Error in main workflow loop: {e} | {tb_flat}")

        time.sleep(10)


def main():
    # [Rule 7] stdio reconfigure 僅於主入口執行，並包 try/except（pythonw 防護）
    try:
        safe_reconfigure_stdio()
    except Exception:
        pass

    parser = argparse.ArgumentParser()
    parser.add_argument("--one-shot", action="store_true", help="Run once and exit instead of loop")
    parser.add_argument("--chunking-only", action="store_true", help="Only run local chunking steps (preprocess, chunk planner)")
    args = parser.parse_args()

    paths = ensure_dirs()
    lock_file = os.path.join(paths.get("manifests_dir", "."), "workflow.lock")
    lock = SingleInstanceLock(lock_file)

    if not lock.acquire():
        try:
            print(f"[Workflow Lock] Another instance of run_workflow is already running (locked on {lock_file}). Exiting.")
        except Exception:
            pass
        sys.exit(0)

    try:
        if args.one_shot:
            log_workflow("Workflow Engine: Running in one-shot mode." + (" [僅切片模式]" if args.chunking_only else ""))
            scan_new_files()
            process_active_tasks(args.chunking_only)
        else:
            run_loop(args.chunking_only)
    finally:
        lock.release()


if __name__ == "__main__":
    main()
