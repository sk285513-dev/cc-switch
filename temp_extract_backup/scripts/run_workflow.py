import os
import sys, io
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
import sys
import time
import json
import argparse
import threading
import subprocess
import random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

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
from workflow_helper import ensure_dirs, log_workflow, log_error
from scripts.quota_manager import QuotaManager

def is_pipeline_blocked_by_validation():
    """檢查是否有任何任務驗證失敗，若有則暫停全線派發等待人工排解"""
    manifests_dir = Path("A:/manifests")
    for p in manifests_dir.glob("task_*.json"):
        if "_chunks" in p.name:
            continue
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            status = str(data.get("status", ""))
            if status.startswith("failed_validation"):
                return True
        except Exception:
            pass
    return False

def get_mock_legal_transcript(index):
    topics = [
        ("民法總則_法律行為之效力", "本課堂主要講解民法總則中有關法律行為之效力。法律行為以意思表示為要素，若意思表示有瑕疵，如詐欺或脅迫，得於知悉後一年內撤銷其意思表示。行為能力制度旨在保護限制行為能力人，限制行為能力人所為之單獨行為，無效。"),
        ("民法債編_侵權行為責任要件", "今天探討民法第一百八十四條獨立侵權行為責任之成立要件。因故意或過失，不法侵害他人之權利者，負損害賠償責任。消滅時效自請求權人知悉有損害及賠償義務人時起算，二年內不行使而消滅。"),
        ("民法物權_共有物之處分與管理", "共有物之處分、變更及設定負擔，應得共有人全體之同意。但依土地法第三十四條之一，共有人人數及應有部分合計過半數即可。共有物分割協議須全體同意始生效力。"),
        ("土地法_土地登記效力與絕對效力", "土地登記規則規定，依本法所為之登記，有絕對效力。第三人信賴登記而取得土地權利者，其權利受法律保護，以維護交易安全。未登記土地所有權處分受限。"),
        ("土地稅法_地價稅減免與申報要件", "土地稅法規定，自用住宅用地之地價稅按千分之二課徵。其餘非自用住宅用地則按基本稅率課徵，符合一定要件之公有土地得申請免稅。"),
        ("民事訴訟法_管轄權與合意管轄", "民事訴訟法規定，訴訟由被告住所地之法院管轄。但當事人得以書面合意約定第一審管轄法院，此即為合意管轄之要件與程序。因不動產涉訟者，專屬不動產所在地法院管轄。"),
        ("行政程序法_行政處分之定義與撤銷", "行政處分係指行政機關就公法上具體事件所為之決定或其他公權力措施，而對外直接發生法律效果之單方行政行為。違法行政處分得由原處分機關或上級機關依法撤銷。"),
        ("刑法總則_正當防衛與緊急避難", "對於現在不法之侵害，而出於防衛自己或他人權利之行為，不罰，此為正當防衛。因避免自己或他人生命、身體、自由、財產之緊急危難，而出於不得已之行為，不罰，此為緊急避難。"),
        ("公司法_股東會召集程序與決議", "公司法規定，股東常會之召集，應於二十日前通知各股東；股東臨時會之召集，則應於十日前通知各股東。股東會決議分普通決議與特別決議。"),
        ("勞動基準法_勞動契約終止與資遣費", "勞動基準法保障勞工權益，規定雇主終止勞動契約時，應依勞工工作年資給予預告期間，並依法給付資遣費。定期契約與不定期契約之認定標準不同。"),
        ("專利法_發明專利三要件", "專利法規定發明專利必須具備產業利用性、新穎性及進步性。申請專利應向專利專責機關提出申請書、說明書及必要圖式。專利權期限自申請日起算二十年。"),
        ("著作權法_合理使用與侵權責任", "著作權法為協調社會公共利益，規定在合理範圍內，得合理使用他人已公開發表之著作，並應明示出處及合理引用。擅自重製他人著作者應負侵權賠償責任。"),
        ("票據法_票據權利消滅時效", "票據法規定執票人對匯票承兌人及本票發票人之權利，自到期日起算，三年間不行使，因時效而消滅。支票權利時效為一年，對前手之追索權為四個月。"),
        ("保險法_保險利益之存在與認定", "保險法規定要保人對於被保險人之生命或身體，應具有保險利益。無保險利益之保險契約，其契約為無效，以防道德危險。財物保險亦須有保險利益。"),
        ("強制執行法_查封程序與效力", "強制執行法規定查封之效力。實施查封後，債務人對查封物所為之處分，對於債權人不生效力。查封得由執行法官指派書記官進行動產或不動產之限制處分。"),
        ("國家賠償法_公務員責任與國賠要件", "國家賠償法規定公務員於執行職務行使公權力時，因故意或過失不法侵害人民自由或權利者，國家應負損害賠償責任。賠償請求應先以書面向賠償義務機關協議。"),
        ("行政訴訟法_撤銷訴訟與訴願程序", "行政訴訟法規定，人民不服訴願決定者，得向行政法院提起撤銷訴訟。撤銷訴訟之提起，應於訴願決定書送達後二個月內之法定期間內為之。"),
        ("消費者保護法_郵購買買七日猶豫期", "消費者保護法規定郵購或訪問買賣之消費者，對所收受之商品不願買受時，得於收受商品後七日內，退回商品或書面通知解除契約，無須說明理由及負擔費用。"),
        ("公寓大廈管理條例_規約與區分所有", "公寓大廈區分所有權人會議之決議，對於區分所有權人及住戶均有拘束力。規約為管理公寓大廈之共同遵守事項，須報請地方主管機關備查。"),
        ("家庭暴力防治法_保護令申請與執行", "家庭暴力防治法規定，法院得依被害人申請核發通常保護令、暫時保護令或緊急保護令。違反保護令罪者，處三年以下有期徒刑、拘役或科或併科罰金。"),
        ("信託法_信託財產獨立性原則", "信託法規定信託財產具有獨立性，受託人因信託財產關係對他人所負之債務，僅得以信託財產為限負其履行責任。信託財產原則上不得強制執行。"),
        ("公平交易法_限制競爭與聯合行為", "公平交易法旨在維護交易秩序與消費者利益。事業不得為聯合行為或濫用市場優勢地位，亦不得為限制競爭或不正競爭之行為。違反者處以行政罰鍰。"),
        ("營業秘密法_損害賠償與懲罰性賠償", "營業秘密法規定，故意洩漏或盜用他人營業秘密者，應負損害賠償責任。法院得依侵害情節，酌定三倍以下之懲罰性賠償。侵害營業秘密罪最重可處五年有期徒刑。"),
        ("金融消費者保護法_金融爭議評議", "金融消費者與金融服務業發生爭議時，得向評議機構申請評議。評議決定在一定額度內對金融服務業具有拘束力，以保護弱勢金融消費者。"),
        ("個人資料保護法_蒐集處理與告知義務", "個人資料保護法規定公務或非公務機關蒐集個人資料時，應向當事人明確告知蒐集目的、類別及利用期間、地區與對象。違反者負有民刑事及行政責任。"),
        ("破產法_破產宣告與和解程序", "破產法規定，法院為破產宣告時，應選任破產管理人，並決定債權申報期間。破產人對其財產之處分權即行喪失，應全權移交破產管理人。"),
        ("仲裁法_仲裁協議效力與仲裁判斷", "仲裁法規定當事人約定將爭議提交仲裁者，法院應依當事人聲請裁定停止訴訟程序，命當事人依約進行仲裁。仲裁判斷與法院確定判決有同一效力。"),
        ("海商法_載貨證券之物權效力", "海商法規定運送人或船長發給載貨證券後，對於載貨證券持有人應負依載貨證券所載內容交付貨物之責任。載貨證券之交付具物權效力。"),
        ("涉外民事法律適用法_準據法之選定", "涉外民事法律適用法旨在解決涉外事件之法律衝突。法律行為之準據法，依當事人意思表示所定之法律；無約定者依關係最切地法，如不動產所在地法。"),
        ("家事事件法_調解程序與非訟事件", "家事事件法規定家事事件除法律另有規定外，於起訴前應經法院調解程序。調解成立者，與確定判決有同一之效力，並能聲請強制執行。")
    ]
    if 1 <= index <= 30:
        return topics[index - 1]
    return ("通用法律教材", "本課堂主要介紹臺灣法律實務與救濟程序，涵蓋民刑事實體法與程序法之基本概念。")

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
      0   → mock 測試任務
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
      95  → 稅法、稅捐稽徵（非主科）
      98  → 證交法、金融法規（非主科）
      100 → 其他未分類
    """
    name = source_name.lower()
    
    # -100. 舊版無備份引擎之 88 堂課程強制置頂
    try:
        import json
        old_courses_path = r"C:\LocalAI_Workstation\old_engine_courses.json"
        if __import__("os").path.exists(old_courses_path):
            with open(old_courses_path, "r", encoding="utf-8") as f:
                old_courses = json.load(f)
                # Check if the source name matches any of the old courses
                for old_c in old_courses:
                    # old_c is like [course]_[video] (e.g. 刑法_刑法_ch01)
                    if old_c.lower() in name or name in old_c.lower():
                        return -100
    except Exception as e:
        pass

    # 0. mock 測試任務（最優先，維持 CI 正常）
    if "mock_" in name or "lexmind_mock_" in name:
        return 0

    # 10. 憲法（根本大法）
    if any(kw in name for kw in ["憲法", "憲政"]):
        return 10

    # 20. 民法（最重要主科，含身分法）
    if any(kw in name for kw in ["民法", "身分法"]):
        return 20

    # 25. 刑法
    if "刑法" in name:
        return 25

    # 30. 行政法（含行政程序法、國家賠償、立法程序與技術）
    if any(kw in name for kw in ["行政法", "行政程序", "國家賠償", "國賠", "立法程序與技術"]):
        return 30

    # 40. 程序法（民訴、刑訴、家事、強執、法院組織法等）
    if any(kw in name for kw in [
        "民事訴訟", "民訴", "刑事訴訟", "刑訴",
        "行政訴訟", "強制執行", "強執", "家事事件", "家事", "程序法", "法院組織法"
    ]):
        return 40

    # 50. 土地法規核心（地政士高考主科：土地法、土地稅法、不動產估價等）
    if any(kw in name for kw in [
        "土地法", "土地登記", "土登", "地籍測量", "地籍",
        "土地法規", "地政法規", "土地稅法", "不動產估價"
    ]):
        return 50

    # 60. 商事法核心與其他特別法（公司法/票據/保險/海商/證交/稅法/智財/勞社/關稅 等）
    if any(kw in name for kw in [
        "公司法", "票據", "保險法", "海商", "海洋法",
        "證交法", "證券交易", "金融法", "銀行法", "期貨",
        "稅法", "稅捽", "稅務", "所得稅", "智慧財產權", "智財",
        "勞動社會", "關稅法規"
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
#   15 workers × 3 chunks = 45 同時上傳
#   每路: 277/45 = 6.16 Mbps → 上傳 29s << API 75s（網路完全不是瓶頸）
#   RPM/key = 4.8（安全閾值 10 RPM）
#   瓶頸：API 配額（59 keys × 1500 RPD ÷ 30 calls = 2,950 tasks/day）
#   552 堂預計完成時間：4.5 小時
# ════════════════════════════════════════════════════════════
# ── 並發數設定（實測邊界值，非理論值）────────────────────────────────
# CPU 密集（FFmpeg Preprocess）：實測 3 workers ≈ 56% CPU，安全上限
PREPROCESS_CONCURRENCY   = 3
# STT 並發上下限：依實測監控統計調整
# 實測資料：並發=10 + 清除死 key 後 → 23.5/hr，並發=28 → 0/hr（全 503）
STT_CONCURRENCY_MIN      = 4    # 最低保底
STT_CONCURRENCY_MAX      = 6    # 避免顯示卡過熱藍白當機下修上限
STT_CONCURRENCY_DEFAULT  = 6    # 無 KPI 資料時預設值下修
# KPI 目標（completed/hr）
KPI_TARGET               = 40

# ── 503 雪崩狀態追蹤（模組層級全域，不需持久化）────────────────────────────
# _avalanche_floor = None  表示目前無雪崩
# _avalanche_floor = N     表示目前強制壓低並發到 N，等待恢復
_avalanche_floor: "int | None" = None
_avalanche_last_503_ts: float = 0.0   # 最近一次 503 的 epoch timestamp


def detect_503_avalanche_floor() -> "int | None":
    """
    讀取 chunk_errors.log 過去 3 分鐘的 503 錯誤數量。
    若 503 頻率超過閾值，回傳「資料驅動的安全地板並發數」；否則回傳 None。

    安全地板計算邏輯（實測資料驅動）：
      - 從 kpi_state.json 讀取「上一個成功輪次的並發數」
      - 地板 = max(上次成功並發 // 2, STT_CONCURRENCY_MIN)
      - 若無歷史資料，地板 = STT_CONCURRENCY_MIN

    觸發閾值：3 分鐘內出現 >= 5 個 503 錯誤
    （依據 AGENTS.md 實測：並發=10 → 23.5/hr，並發=28 → 0/hr 雪崩）
    """
    import re, time as _time
    from datetime import datetime as _dt, timedelta as _td
    from pathlib import Path
    import json

    error_log = Path("A:/logs/chunk_errors.log")
    if not error_log.exists():
        return None

    cutoff = _dt.utcnow() + _td(hours=8) - _td(minutes=3)
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
    try:
        if Path(kpi_state_path).exists():
            s = json.loads(Path(kpi_state_path).read_text(encoding="utf-8"))
            v = int(s.get("stt_concurrency", STT_CONCURRENCY_DEFAULT))
            if v > 0:
                last_good = v
    except Exception:
        pass

    # 安全地板 = 上次並發的一半，但不低於 STT_CONCURRENCY_MIN
    floor = max(last_good // 2, STT_CONCURRENCY_MIN)
    log_workflow(
        f"[503-Avalanche] 偵測到 {count_503} 個 503（3min 內），"
        f"上次並發={last_good} → 安全地板={floor}（實測資料驅動）"
    )
    return floor


def compute_adaptive_concurrency() -> int:
    """
    依最近 KPI 歷史動態決定 STT 並發數。
    規則（實測資料驅動，非時間硬編碼）：
      - KPI >= target*1.5 (60/hr)：並發充足，保持目前值
      - KPI >= target (40/hr)：剛好達標，小幅加大備用
      - KPI >= target*0.5 (20/hr)：差一點，加大 +4
      - KPI >= target*0.25 (10/hr)：明顯不足，加大 +8
      - KPI <  target*0.25 (<10/hr) 或 全 0：大幅拉升至上限
      - KPI 資料不足 < 3 筆：用預設值
    """
    global _avalanche_floor, _avalanche_last_503_ts
    import json, os, re, time as _time
    from datetime import datetime, timedelta
    from pathlib import Path

    kpi_state_path = "A:/logs/kpi_state.json"

    # ── Step 0: 503 雪崩優先偵測（30 秒內立刻反應，最高優先）────────────────
    avalanche_floor = detect_503_avalanche_floor()
    if avalanche_floor is not None:
        # 進入雪崩模式：強制壓低並發，記錄時間戳
        _avalanche_floor = avalanche_floor
        _avalanche_last_503_ts = _time.time()
        try:
            s = json.loads(Path(kpi_state_path).read_text(encoding="utf-8")) if Path(kpi_state_path).exists() else {}
            s["stt_concurrency"] = _avalanche_floor
            s["avalanche_mode"] = True
            Path(kpi_state_path).write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
        log_workflow(f"[503-Avalanche] 強制並發={_avalanche_floor}（安全地板，等待 API 恢復）")
        return _avalanche_floor
    elif _avalanche_floor is not None:
        # 雪崩已緩解：緩慢恢復（每輪 +1，最多到 STT_CONCURRENCY_MAX）
        elapsed = _time.time() - _avalanche_last_503_ts
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
    if os.path.exists(kpi_state_path):
        try:
            s = json.load(open(kpi_state_path, encoding="utf-8"))
            v = s.get("kpi_b1", None)
            if v is not None:
                kpi_vals.append(float(v))
        except Exception:
            pass

    # 2. 讀 kpi_monitor.log 最近 30 分鐘的 KPI-B1 樣本
    kpi_log_path = "A:/logs/kpi_monitor.log"
    if os.path.exists(kpi_log_path):
        try:
            cutoff = datetime.utcnow() - timedelta(minutes=30)
            for l in open(kpi_log_path, encoding="utf-8", errors="replace").readlines()[-120:]:
                m = re.search(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\].*KPI-B1: ([\d.]+)", l)
                if m:
                    ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
                    if ts > cutoff:
                        kpi_vals.append(float(m.group(2)))
        except Exception:
            pass

    # 3. 樣本不足：用預設值
    if len(kpi_vals) < 3:
        return STT_CONCURRENCY_DEFAULT

    # 4. 取近期平均（排除極端離群）
    kpi_vals.sort()
    trimmed = kpi_vals[len(kpi_vals)//5 : -len(kpi_vals)//5 or None] or kpi_vals
    recent_kpi = sum(trimmed) / len(trimmed)

    # 5. 讀目前正在使用的並發數（上一輪設定值，存在 kpi_state）
    try:
        s = json.load(open(kpi_state_path, encoding="utf-8"))
        current = int(s.get("stt_concurrency", STT_CONCURRENCY_DEFAULT))
    except Exception:
        current = STT_CONCURRENCY_DEFAULT

    # 6. KPI 回饋規則（含「並發過高反而更差」偵測）
    if recent_kpi >= KPI_TARGET * 1.5:
        new = max(current - 2, STT_CONCURRENCY_MIN)   # 有餘裕，可略降節省資源
        reason = f"KPI {recent_kpi:.1f} ≥ 60，充裕，略降並發"
    elif recent_kpi >= KPI_TARGET:
        new = current                                   # 剛好達標，不動
        reason = f"KPI {recent_kpi:.1f} ≥ 40，達標，維持 {current}"
    elif recent_kpi >= KPI_TARGET * 0.5:
        new = min(current + 2, STT_CONCURRENCY_MAX)    # 差一點，小幅加 2
        reason = f"KPI {recent_kpi:.1f} 20~40，不足，+2"
    elif recent_kpi > 0:
        # KPI 低但不是 0：適度增加
        new = min(current + 2, STT_CONCURRENCY_MAX)
        reason = f"KPI {recent_kpi:.1f} 0~20，明顯不足，+2"
    else:
        # KPI = 0：「可能是並發過高造成雪崩」vs「並發不夠」
        # 若目前並發已高（≥12），先降並發（解除 thundering herd）
        # 若目前並發低（<12），再嘗試增加
        if current >= 12:
            new = max(current - 4, STT_CONCURRENCY_MIN)
            reason = f"KPI=0 且並發={current}≥12，疑似 API 雪崩，降並發 -4"
        else:
            new = min(current + 2, STT_CONCURRENCY_MAX)
            reason = f"KPI=0 且並發={current}<12，適度增加 +2"

    # 7. 回寫並發數到 kpi_state 供下一輪讀取
    try:
        s = json.load(open(kpi_state_path, encoding="utf-8")) if os.path.exists(kpi_state_path) else {}
        s["stt_concurrency"] = new
        json.dump(s, open(kpi_state_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    except Exception:
        pass

    import logging
    logging.info(f"[AdaptiveConcurrency] {reason} → 並發={new}（樣本={len(kpi_vals)}, 近期KPI均值={recent_kpi:.1f}）")
    return new


TASK_CONCURRENCY = STT_CONCURRENCY_DEFAULT  # 初始值，會被 compute_adaptive_concurrency() 覆蓋



def run_single_task_safe(manifest: dict, manifest_path: Path, exclusive_key: str, qm: QuotaManager, chunking_only: bool) -> bool:
    """
    包裝單一任務的完整流程，供 ThreadPoolExecutor 並列呼叫。
    ★ Fix ❷：exclusive_key 可為 None，此時在 Worker 啟動時才向 qm 按需取得，
              確保 key 不被預先鎖死在等待佇列中。
    返回 True 表示任務成功。
    """
    paths = ensure_dirs()
    task_id = manifest["task_id"]
    key_acquired_here = False

    # ★ 按需取得 key（若呼叫方沒有預先分配）
    if not chunking_only and exclusive_key is None and qm is not None:
        try:
            exclusive_key = qm.acquire_key_exclusive()
            key_acquired_here = True
            log_workflow(f"[Parallel Dispatcher] Task {task_id} 開始，按需取得金鑰: {exclusive_key[:8]}...")
        except RuntimeError:
            log_error(f"[Parallel Dispatcher] Task {task_id} 無可用金鑰，跳過本輪。")
            return False
    elif exclusive_key:
        log_workflow(f"[Parallel Dispatcher] Task {task_id} 開始，使用傳入金鑰: {exclusive_key[:8]}...")
    else:
        log_workflow(f"[Parallel Dispatcher] Task {task_id} 開始（chunking-only 模式）")

    try:
        return _run_task_steps(manifest, manifest_path, paths, exclusive_key, chunking_only)
    except Exception as e:
        log_error(f"[Parallel Dispatcher] Task {task_id} 發生異常：{e}")
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                current_manifest = json.load(f)
            current_manifest["status"] = "failed"
            current_manifest["error"] = str(e)
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(current_manifest, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        return False
    finally:
        # ★ 只有本函式自己取的 key 才在這裡釋放
        if key_acquired_here and qm and exclusive_key:
            qm.release_key(exclusive_key)

def process_active_tasks(chunking_only=False):
    paths = ensure_dirs()
    manifests_dir = paths["manifests_dir"]
    
    # 尋找所有非 chunks 且未完成/未失敗的任務清單
    manifest_paths = Path(manifests_dir).glob("*.json")
    active_tasks = []
    
    for p in manifest_paths:
        if not p.name.startswith("task_") or p.name.endswith("_chunks.json"):
            continue
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                status = data.get("status")
                # 在 chunking_only 模式下，如果 chunk_planner 已經 completed，我們跳過此任務
                if chunking_only and data.get("steps", {}).get("chunk_planner") == "completed":
                    continue
                if status not in ["completed", "failed"]:
                    active_tasks.append((p, data))
        except Exception:
            pass
            
    # 依照「先程序後實體、國考主要科目優先、再來分科」的法學專業排序佇列
    active_tasks.sort(key=lambda x: (
        get_legal_priority_score(x[1].get("source_name", "")),
        x[1].get("task_id", "")
    ))
    
    # 暫時鎖定僅執行第一堂課已測試完畢，註解此行以解鎖所有課程排程
    # active_tasks = [t for t in active_tasks if t[1].get("task_id") == "task_20260706_201825_00_3231"]
            
    if not active_tasks:
        return

    log_workflow(f"Workflow Engine: Found {len(active_tasks)} active tasks to process.")

    # ── 建立全局共享的 QuotaManager 實例 ──
    try:
        qm = QuotaManager()
    except Exception as qm_err:
        log_error(f"QuotaManager 初始化失敗，回退至單線程模式：{qm_err}")
        qm = None

    # ── 雙階段自適應並發數選擇 ──
    # Phase A (NOW）16:00): queued > chunked → 用 PREPROCESS_CONCURRENCY=3
    # Phase B (16:00+):      強制 STT_CONCURRENCY=15，並把 chunked 任務排到最前面
    import datetime as _dt
    # 《重要》必須用台灣時間 UTC+8，不能用 datetime.now()（這是 UTC）
    _tw_now = _dt.datetime.utcnow() + _dt.timedelta(hours=8)
    _now_hour = _tw_now.hour
    _is_stt_phase = _now_hour >= 16 or _now_hour < 8   # 16:00-08:00 台灣時間走 STT Phase B

    queued_count  = sum(1 for _, d in active_tasks if d.get("status") == "queued")
    chunked_count = sum(1 for _, d in active_tasks if d.get("status") == "chunked")

    if _is_stt_phase or chunked_count > 0:
        # ── KPI 回饋自動調節（取代時間硬編碼）──
        effective_concurrency = compute_adaptive_concurrency()
        chunked_tasks = [(p, d) for p, d in active_tasks if d.get("status") == "chunked"]
        other_tasks   = [(p, d) for p, d in active_tasks if d.get("status") != "chunked"]
        active_tasks  = chunked_tasks + other_tasks
        log_workflow(f"[Dispatcher] ✅ STT Phase B ({chunked_count} chunked + {queued_count} queued) 並發={effective_concurrency}（KPI自適應）")
    elif queued_count > chunked_count:
        # Phase A: queued 任務排首，確保 preprocess 真正執行
        effective_concurrency = PREPROCESS_CONCURRENCY
        queued_tasks = [(p, d) for p, d in active_tasks if d.get("status") == "queued"]
        other_tasks  = [(p, d) for p, d in active_tasks if d.get("status") != "queued"]
        active_tasks = queued_tasks + other_tasks
        log_workflow(f"[Dispatcher] Preprocess Phase A ({queued_count} queued 優先 + {chunked_count} chunked) → 並發={effective_concurrency}（CPU 安全）")
    else:
        effective_concurrency = STT_CONCURRENCY
        log_workflow(f"[Dispatcher] 佇列以 STT 為主 ({chunked_count} chunked vs {queued_count} queued) → 並發={effective_concurrency}（網路最佳）")

    batch = active_tasks[:effective_concurrency * 3]
    log_workflow(f"[Parallel Dispatcher] 本輪提交 {len(batch)}/{len(active_tasks)} 個任務（並發數 {effective_concurrency}）")


    with ThreadPoolExecutor(max_workers=effective_concurrency) as executor:
        futures = {}
        for i, (manifest_path, manifest) in enumerate(batch):
            # ── 分批啟動小時差：3~8 秒隨機間隔（避免同一毫秒發起）──
            if i > 0:
                stagger = random.uniform(3, 8)
                time.sleep(stagger)
            fut = executor.submit(
                run_single_task_safe,
                manifest,
                manifest_path,
                None,   # ★ 不預傳 key，Worker 自行按需取得
                qm,
                chunking_only,
            )
            futures[fut] = manifest["task_id"]

        for future in as_completed(futures):
            task_id = futures[future]
            try:
                success = future.result()
                status = "success" if success else "failed"
                log_workflow(f"[Parallel Dispatcher] Task {task_id} 完成，狀態：{status}")
            except Exception as e:
                log_error(f"[Parallel Dispatcher] Task {task_id} Future 異常：{e}")

    # 若本輪還有剩餘任務，交由 run_loop 下一輪迭代處理（不遞迴，避免爆棧）
    remaining = len(active_tasks) - len(batch)
    if remaining > 0:
        log_workflow(f"[Parallel Dispatcher] 本輪完成，剩餘 {remaining} 個任務等待下一輪。")

# ── 背景 Pipeline Daemon：自動推進 stt→merge→formatter ──
_pipeline_lock = threading.Lock()
_pipeline_running = set()  # 正在執行 merge/fmt 的 task_id 集合
MAX_CONCURRENT_FORMATTERS = 2  # 最多同時 2 個 formatter（防 OpenCV OOM）

def _spawn_step(task_id: str, script: str, step_name: str):
    """以獨立 subprocess fire-and-forget 方式啟動下一步驟。"""
    with _pipeline_lock:
        key = f"{task_id}:{step_name}"
        if key in _pipeline_running:
            return  # 已在執行中，避免重複啟動
        _pipeline_running.add(key)

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    script_path = str(Path(__file__).parent / script)
    proc = subprocess.Popen(
        [sys.executable, script_path, "--task-id", task_id],
        env=env,
        cwd=str(Path(__file__).parent.parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    log_workflow(f"[PipelineDaemon] Spawned {step_name} for {task_id} (pid={proc.pid})")

    def _wait_and_cleanup():
        proc.wait()
        with _pipeline_lock:
            _pipeline_running.discard(key)
        log_workflow(f"[PipelineDaemon] {step_name} for {task_id} finished (rc={proc.returncode})")

    t = threading.Thread(target=_wait_and_cleanup, daemon=True)
    t.start()


def pipeline_daemon_tick():
    """掃描所有 manifest，找出卡在 stt=completed 或 merge=completed 的任務，自動補發。
    
    安全保護：在 spawn merge 前驗證所有 chunk .txt 是否真實存在。
    若缺失，重置 stt=pending，防止無窮迴圈派發失敗的 merge。
    """
    manifests_dir = Path("A:/manifests")
    for mf in manifests_dir.glob("task_*.json"):
        if "_chunks" in mf.name:
            continue
        try:
            with open(mf, encoding="utf-8") as f:
                m = json.load(f)
            task_id = m.get("task_id", "")
            steps = m.get("steps", {})
            status = m.get("status", "")
            if status in ("completed", "failed"):
                continue

            # stt 完成但 merge 還沒做 → 先驗證 .txt 存在，再啟動 merge
            if steps.get("stt") == "completed" and steps.get("merge") == "pending":
                cm = str(mf).replace(".json", "_chunks.json")
                chunks_ok = False
                if os.path.exists(cm):
                    try:
                        chunks = json.load(open(cm, encoding="utf-8"))
                        done = [c for c in chunks if c.get("status") == "completed"]
                        # 驗證每個 completed chunk 的 .txt 是否真實存在
                        txt_dir = f"A:/chunks/{task_id}"
                        missing = [
                            c for c in done
                            if not os.path.exists(
                                os.path.join(txt_dir, c["filename"].replace(".wav", ".txt"))
                            )
                        ]
                        if missing:
                            # 有假完成 chunk → 重置回 pending 防止無窮 merge 迴圈
                            for c in missing:
                                c["status"] = "pending"
                                c["retry_count"] = 0
                            with open(cm, "w", encoding="utf-8") as cf:
                                json.dump(chunks, cf, ensure_ascii=False, indent=2)
                            m["steps"]["stt"] = "pending"
                            with open(mf, "w", encoding="utf-8") as mff:
                                json.dump(m, mff, ensure_ascii=False, indent=2)
                            log_workflow(
                                f"[PipelineDaemon] 重置 {task_id[-4:]} stt=pending"
                                f"（{len(missing)} 個 chunk 缺失 .txt）"
                            )
                        elif done and len(done) == len(chunks):
                            chunks_ok = True
                    except Exception:
                        pass

                if chunks_ok:
                    _spawn_step(task_id, "merge_transcript.py", "merge")

            # merge 完成但 formatter 還沒做 → 啟動 formatter（限制並發數）
            # 【修復】formatter key 缺失（None）等同 pending，避免靜默跳過
            elif steps.get("merge") == "completed" and steps.get("formatter") in ("pending", None):
                # 確保 manifest 有 formatter:pending（補寫缺失的欄位）
                if steps.get("formatter") is None:
                    m["steps"]["formatter"] = "pending"
                    with open(mf, "w", encoding="utf-8") as mff:
                        json.dump(m, mff, ensure_ascii=False, indent=2)
                # 計算目前正在跑的 formatter 數量
                with _pipeline_lock:
                    active_fmts = sum(1 for k in _pipeline_running if k.endswith(":formatter"))
                if active_fmts < MAX_CONCURRENT_FORMATTERS:
                    _spawn_step(task_id, "markdown_formatter.py", "formatter")
                # else: 超過上限，等下一輪 tick（20 秒後）再補
        except Exception:
            pass



def _start_pipeline_daemon():
    """啟動背景 Daemon Thread，每 20 秒掃描一次流水線卡點。"""
    def _loop():
        while True:
            try:
                if is_pipeline_blocked_by_validation():
                    time.sleep(30)
                    continue
                pipeline_daemon_tick()
            except Exception as e:
                log_error(f"[PipelineDaemon] tick error: {e}")
            time.sleep(20)
    t = threading.Thread(target=_loop, daemon=True, name="PipelineDaemon")
    t.start()
    log_workflow("[PipelineDaemon] 背景自動流水線推進服務已啟動（每 20 秒掃描）")


def _run_task_steps(manifest: dict, manifest_path: Path, paths: dict, exclusive_key: str, chunking_only: bool) -> bool:
    """
    執行單一任務的工作流步驟。
    STT 完成後立即返回（不等 merge/formatter），由 PipelineDaemon 自動推進後續步驟。
    exclusive_key: 多工模式下此 Task 獨佔的 API 金鑰，傳遞給 run_stt()。
    返回 True 表示 STT 步驟成功（或已跳過）。
    """
    task_id = manifest["task_id"]
    source_name = manifest["source_name"]

    # ★ 相容變山：舊格式 manifest 用 video_path，新格式用 source_path
    if "source_path" not in manifest and "video_path" in manifest:
        manifest["source_path"] = manifest["video_path"]
        try:
            with open(manifest_path, "w", encoding="utf-8") as _f:
                json.dump(manifest, _f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ── Mock 模式 ──
    if "mock_" in source_name or "lexmind_mock_" in source_name:
        log_workflow(f"Workflow Engine: [MOCK MODE] Processing task {task_id}...")
        try:
            import re
            for step in ["preprocess", "chunk_planner", "stt", "merge", "formatter"]:
                manifest["steps"][step] = "completed"
                with open(manifest_path, "w", encoding="utf-8") as f:
                    json.dump(manifest, f, ensure_ascii=False, indent=2)
                time.sleep(0.1)

            manifest["status"] = "completed"
            try:
                idx_match = re.search(r"mock_lesson_(\d+)", source_name)
                idx = int(idx_match.group(1)) if idx_match else 1
            except Exception:
                idx = 1
            topic_title, topic_content = get_mock_legal_transcript(idx)

            base_name = os.path.splitext(source_name)[0]
            processed_dir = Path("A:/processed_md")
            processed_dir.mkdir(parents=True, exist_ok=True)

            md_path = processed_dir / f"{base_name}.md"
            srt_path = processed_dir / f"{base_name}.srt"
            vtt_path = processed_dir / f"{base_name}.vtt"
            txt_path = processed_dir / f"{base_name}.txt"
            idx_path = processed_dir / f"{base_name}_index.json"

            manifest["output_markdown"] = str(md_path)
            manifest["output_srt"] = str(srt_path)
            manifest["output_vtt"] = str(vtt_path)
            manifest["output_txt"] = str(txt_path)
            manifest["output_json_index"] = str(idx_path)

            with open(md_path, "w", encoding="utf-8") as wf:
                wf.write(f"# {base_name} - {topic_title}\n\n{topic_content}\n")
            with open(srt_path, "w", encoding="utf-8") as wf:
                wf.write(f"1\n00:00:01,000 --> 00:00:15,000\n{topic_title}")
            with open(vtt_path, "w", encoding="utf-8") as wf:
                wf.write(f"WEBVTT\n\n1\n00:00:01.000 --> 00:00:15.000\n{topic_title}")
            with open(txt_path, "w", encoding="utf-8") as wf:
                wf.write(f"{topic_title}。{topic_content}")
            with open(idx_path, "w", encoding="utf-8") as wf:
                json.dump({"title": f"{base_name} - {topic_title}", "summary": topic_content, "terms": [topic_title]}, wf, ensure_ascii=False, indent=2)

            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)

            log_workflow(f"Workflow Engine: [MOCK MODE] Task {task_id} completed successfully!")
            return True
        except Exception as e:
            log_error(f"Workflow Engine: [MOCK MODE] Critical error in task {task_id}: {e}")
            manifest["status"] = "failed"
            manifest["error"] = str(e)
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            return False

    # ── 真實任務步驟 ──
    try:
        # 步驟二：Preprocess
        if manifest["steps"]["preprocess"] == "pending":
            success = preprocess(task_id)
            if not success:
                raise RuntimeError("Preprocess step failed")
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

        # 步驟三：Chunk Planner
        if manifest["steps"]["chunk_planner"] == "pending":
            success = plan_chunks(task_id)
            if not success:
                raise RuntimeError("Chunk planning step failed")
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

        if chunking_only:
            log_workflow(f"Workflow Engine: Task {task_id} chunking done. Stopping (--chunking-only mode).")
            return True

        # 步驟四：STT（傳入排他金鑰供並列模式使用）
        if manifest["steps"]["stt"] == "pending":
            success = run_stt(task_id, exclusive_key=exclusive_key)
            if not success:
                raise RuntimeError("STT transcription step failed")
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

        # STT 完成後立即 fire-and-forget merge，不阻塞 Worker 線程
        # PipelineDaemon 也會在 20 秒後自動補發，此處為即時觸發優化
        if manifest["steps"].get("stt") == "completed" and manifest["steps"].get("merge") == "pending":
            _spawn_step(task_id, "merge_transcript.py", "merge")
            log_workflow(f"Workflow Engine: Task {task_id} STT done, merge spawned. Worker released.")

        return True

    except Exception as e:
        log_error(f"Workflow Engine: Critical error in task {task_id}: {e}")
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                current_manifest = json.load(f)
            # ★ 保護：若 stt_runner 已將任務重置為 chunked（等待重試），不要覆寫為 failed
            if current_manifest.get("status") != "chunked":
                current_manifest["status"] = "failed"
                current_manifest["error"] = str(e)
                with open(manifest_path, "w", encoding="utf-8") as f:
                    json.dump(current_manifest, f, ensure_ascii=False, indent=2)
            else:
                log_workflow(f"Workflow Engine: Task {task_id} already reset to chunked by stt_runner, skipping failed overwrite.")
        except Exception as write_err:
            log_error(f"Failed to mark task as failed: {write_err}")
        return False


def run_loop(chunking_only=False):
    log_workflow("臺灣法律教材長影音切片處理工作流監控服務已啟動！" + (" [僅切片模式]" if chunking_only else ""))
    ensure_dirs()
    # 啟動背景 PipelineDaemon（自動推進 merge/formatter，不受 Whisper 阻塞）
    if not chunking_only:
        _start_pipeline_daemon()

    while True:
        try:
            if is_pipeline_blocked_by_validation():
                log_workflow("⚠️ [Hard Gate 阻擋] 偵測到驗收失敗 (failed_validation) 的任務！整個背景自動派發系統已暫停，等待人工排解...")
                time.sleep(30)
                continue
            
            # 1. 掃描新檔案
            scan_new_files()
            # 2. 執行活動中任務（STT 完成後 Worker 立即釋放，merge/fmt 由 Daemon 接手）
            process_active_tasks(chunking_only)
        except RuntimeError as e:
            # 金鑰池全滅（所有 key 都 429）→ 等冷卻期結束
            if "exhausted" in str(e).lower() or "湿" in str(e) or "all api keys" in str(e).lower():
                log_workflow(f"[Quota Cooldown] 金鑰池耗盡，進入 600 秒冷卻睡眠... ({e})")
                time.sleep(600)
                # 重置 key pool state
                try:
                    import json as _json
                    _qstate = Path("config/quota_state.json")
                    _qstate.write_text(_json.dumps({"exhausted_keys": []}, ensure_ascii=False), encoding="utf-8")
                    log_workflow("[Quota Cooldown] 金鑰池已重置，繼續排程。")
                except Exception:
                    pass
            else:
                log_error(f"Error in main workflow loop: {e}")
        except Exception as e:
            log_error(f"Error in main workflow loop: {e}")

        time.sleep(10)


if __name__ == "__main__":
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
            log_workflow("Workflow Engine: Running in one-shot mode." + (" [僅切片模式]" if args.chunking_only else ""))
            scan_new_files()
            process_active_tasks(args.chunking_only)
        else:
            run_loop(args.chunking_only)
    finally:
        lock.release()
