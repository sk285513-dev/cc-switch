# LexMind-Omni 開發進度移交文件 (README_DEVEL.md)

> ⚠️ 新帳號 / 新代理人進入專案時，**必須第一步讀取此文件**，再執行任何操作。

---

## 📅 最後更新：2026-07-12 23:27

---

## 🚫 黃金守則：每次修改程式碼前，必須確認的事項（ALL AGENTS MUST READ）

> **違反以下任一條款，將直接導致整個 Workflow 每 10 秒崩潰一次，且錯誤不顯眼，排查極難。**

### 守則 1：禁止讓 emoji / 非 ASCII 字元進入 print() ，除非該腳本頭部已有 UTF-8 強制修正

**問題根源：** Windows 的 PowerShell / CMD 預設 console 輸出編碼是 `cp950`（繁體中文編碼），它無法表示任何 emoji（如 `✅ ❌ ⚠️ 🚨`）。只要任一腳本呼叫了 `print('✅ ...')` 而 stdout 沒有被強制設為 UTF-8，就會拋出 `UnicodeEncodeError: 'cp950' codec can't encode character`。

**致命性：** 由於 `run_workflow.py` 的主迴圈用 `except Exception` 捕捉所有錯誤並繼續跑，這個 cp950 錯誤不會讓進程死亡，而是讓系統每 10 秒「偽裝成正常在跑、實際上 0 個任務被派出去」，KPI 永遠是 0.0/hr。

**強制修正（每個新建或修改的 .py 腳本，開頭必須加這 4 行）：**

```python
import sys, io
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
```

**已確認修復的腳本清單（2026-07-12）：**
`run_workflow.py` / `stt_runner.py` / `kpi_monitor.py` / `markdown_formatter.py` / `merge_transcript.py` / `preprocess_media.py` / `progress_dashboard.py` / `workflow_helper.py` / `chunk_planner.py` / `watchdog_monitor.py` / `quota_manager.py` / `watchdog.py`

### 守則 2：新增腳本時，第一行必須先驗證

在新建任何 `.py` 腳本後，執行以下快速驗證指令，確認不會有 cp950 地雷：

```powershell
# 確認腳本開頭有 UTF-8 強制修正
Select-String -Path "C:\LocalAI_Workstation\scripts\<新腳本名>.py" -Pattern "reconfigure" | Select-Object LineNumber
```

若輸出為空，表示**尚未加入修正，禁止上線運行**。

### 守則 3：禁止憑直覺大幅修改並發數（詳見 AGENTS.md 第五章）

### 守則 4：禁止在未讀本文件的情況下啟動工作流或修改 scripts/ 下的程式碼

---

## 🏗️ 系統架構

```
C:\LocalAI_Workstation\
├── scripts/
│   ├── run_workflow.py        # 主控制迴圈（PipelineDaemon）N=3 並列
│   ├── stt_runner.py          # Gemini 雲端 STT（主力），Whisper 蒸餾（輔助）
│   ├── merge_transcript.py    # 分片逐字稿合併 + 邊界精校
│   ├── markdown_formatter.py  # 輸出 MD / SRT / VTT / TXT / JSON
│   ├── whisper_pool.py        # 雙 GPU 並列本地蒸餾（float16）
│   ├── watchdog_monitor.py    # 系統守護（自動重啟 workflow，每 15min auto_verify）
│   ├── progress_dashboard.py  # 即時進度儀表板
│   └── auto_verify.py         # 品管驗收腳本
├── config/
│   ├── keys.yaml              # Gemini API 金鑰池
│   └── quota_policy.yaml      # 金鑰輪替與 429 退避策略
└── A:\
    ├── chunks\<task_id>\      # 音訊切片 + 逐字稿 txt（完成後清理）
    ├── manifests\task_*.json  # 任務狀態
    ├── processed_md\          # 最終成品（MD/SRT/VTT/TXT/JSON）
    └── logs\                  # workflow.log, watchdog.log
```

---

## ⚙️ 流水線流程

```
[影片] → preprocess → chunk_planner → STT(Gemini雲端) → merge → formatter → [成品]
                                         ↓ 平行蒸餾
                                    Whisper(本地GPU，輔助)
```

### 關鍵規定
- **STT 主力永遠是 Gemini 雲端**，Whisper 僅作蒸餾輔助，禁止成為主輸出
- `stt_engine` 已硬鎖為 `"gemini"`，有 assert 防呆
- API 429 → 自動退避 + 金鑰池輪替，不崩潰

---

## 📊 目前進度（2026-07-10 02:37）

| 項目 | 數量 |
|---|---|
| 任務總數 | ~600 堂（含新登記 H 碟 123 堂） |
| Formatter 完成（成品落地） | 0（舊 7 堂已清除重跑） |
| 待處理（pending/queued） | ~590 堂 |
| 正在跑（STT/Merge/Format 中） | 依 watchdog 狀態 |

### 處理優先序
| Score | 科目 |
|---|---|
| 10 | 憲法霖洄（19堂，H碟）|
| 20 | 民法A115（47堂）、身分法B115（10堂）、民法B（25+堂）|
| 25 | 刑法 |
| 30 | 行政法霖迴B115（40堂）、行政法A |
| 40 | 家事事件法115（7堂）、刑訴B、民訴 |
| 50 | 土地登記、土地法 |
| 60 | 公司法、票據、保險、**證交法**、**稅法**（同級）|
| 90 | 不動產估價 |

---

## 🐛 已知 Bug 與修復狀態

### ✅ 已修復
1. **SRT 時間戳全為 00:00:00** → 移除錯誤 window 過濾邏輯，改用 `[chunk_start, chunk_end]` 範圍過濾 + 近鄰去重
2. **Whisper 佔用主 STT** → 硬鎖 `stt_engine="gemini"` + POLICY GUARD
3. **課程優先序未生效** → `get_legal_priority_score()` 已完整定義 score 0~100
4. **run_workflow 主迴圈阻塞** → PipelineDaemon tick 機制（watchdog 觸發）

### ⏳ 需持續觀察
- 7 堂錯誤成品已刪除，正在重跑：
  - REFORMAT（有 merged_full）：刑訴B_ch5、稅法_ch14、行政法A_ch34、證交法×2
  - FULL REDO（需重新 STT）：民法B_ch15、土地登記_ch1

---

## 🚨 本次操作意外事故

**2026-07-10 02:33** 執行「清除 J 碟備份」時，因 `manifest.course_dir` 全為空字串，`Path('')` 解析至 `C:\LocalAI_Workstation\` 根目錄，誤刪以下文件：

- `README_DEVEL.md`（此文件，已重建）
- `CLAUDE.md`
- `CONTEXT.md`
- `cursorrules.md`
- `.cursorrules.txt`
- `tmp_md_preview.txt`, `tmp_path.txt`, `tmp_srt_preview.txt`（暫存，不重要）

**實際教材 J 碟備份完全無損**（course_dir 空，根本沒讀到 J 碟）。

---

## 🎯 下一步行動

1. **觀察 watchdog 是否正常重跑 7 堂錯誤課程**
2. **補全 manifest 的 `course_dir` 欄位**（避免類似事故）
3. **驗收第一批重跑結果**（SRT 是否有正確時間戳）
4. **補充重建 CLAUDE.md / CONTEXT.md**（若有需要）
5. 持續監控 `A:\logs\watchdog.log` 確認流水線正常

---

## 🔑 啟動指令

```powershell
# 查看即時進度
cd C:\LocalAI_Workstation
python scripts/progress_dashboard.py

# 查看最新 watchdog 狀態
Get-Content A:\logs\watchdog.log -Tail 20

# 品管驗收
python scripts/auto_verify.py
```


---

## Bug Memory 2026-07-11

### Bug-01 Timezone (Most Critical)
- datetime.now() returns UTC on server, not Taiwan time
- Caused: 345 queued tasks stuck forever (system thought it was STT night phase all day)
- Fix: (datetime.utcnow() + timedelta(hours=8)).hour
- RULE: Always use utcnow()+timedelta(hours=8) for Taiwan time

### Bug-02 Dispatcher Phase A missing reorder
- Phase B put chunked tasks first, Phase A forgot to put queued tasks first
- Fix: added queued_tasks + other_tasks reorder in Phase A

### Bug-03 KPI stuck threshold too small
- KPI_A3_STUCK_REPEAT_LIMIT=6 (30min) << STT task duration (1-2hr)
- Fix: changed to 24 (2 hours)

### Bug-04 skip_stuck_tasks no progress check
- Fix: 3 safety gates: done_chunks>0 / age<2hr / all pass -> only then kill

### Bug-05 check_stuck 10min kill too aggressive
- FFmpeg needs 10+min for 5GB video, was killing normal operations
- Fix: 3-stage escalation: 10min diagnose -> 15min autofix -> 20min alert+kill


---

## Bug Memory 2026-07-11

### Bug-01 Timezone (Most Critical)
- datetime.now() returns UTC on server, not Taiwan time
- Caused: 345 queued tasks stuck forever (system thought it was STT night phase all day)
- Fix: (datetime.utcnow() + timedelta(hours=8)).hour
- RULE: Always use utcnow()+timedelta(hours=8) for Taiwan time

### Bug-02 Dispatcher Phase A missing reorder
- Phase B put chunked tasks first, Phase A forgot to put queued tasks first
- Fix: added queued_tasks + other_tasks reorder in Phase A

### Bug-03 KPI stuck threshold too small
- KPI_A3_STUCK_REPEAT_LIMIT=6 (30min) << STT task duration (1-2hr)
- Fix: changed to 24 (2 hours)

### Bug-04 skip_stuck_tasks no progress check
- Fix: 3 safety gates: done_chunks>0 / age<2hr / all pass -> only then kill

### Bug-05 check_stuck 10min kill too aggressive
- FFmpeg needs 10+min for 5GB video, was killing normal operations
- Fix: 3-stage escalation: 10min diagnose -> 15min autofix -> 20min alert+kill
- RULE: Before killing any process: check errors, try autofix, notify AI first

### Key Pool (2026-07-11)
- Total: 89 keys (key_001 to key_089)
- Daily limit: 89 x 1500 = 133,500 requests

### Model Router (scripts/model_router.py)
- Priority: gemini-3.5-flash -> gemini-3-flash-preview -> gemini-3.1-flash-lite
- Blacklist: gemini-2.5-flash (404), gemini-2.0-flash (limit:0)
- RULE: All model selection only in model_router.py, others call get_router().acquire()

---

## Bug Memory 2026-07-12 (Today's Debugging & Handoff)

### 🚨 System Status upon Reboot
- **Completed:** ~22 tasks (from today's batch)
- **Pending:** ~66 tasks
- **Total:** ~88 tasks in current batch
- **Note:** The user manually deleted old manifests (from prior days) from `A:\manifests` so that the dashboard accurately reflects today's batch. Do NOT restore or search for them.

### Bug-01: Progress Dashboard UI Truncation
- **Issue:** The Dashboard correctly calculated total completed tasks but was hardcoded (`with_ts[:20]`) to only display 20 rows in the table. This confused the user into thinking the total count was wrong.
- **Fix:** Increased the table display limit from `20` to `100` in `scripts/progress_dashboard.py` and adjusted the UI title logic so top and bottom numbers match.

### Bug-02: KPI Monitor Negative Values (-884.9/hr)
- **Issue:** After the user deleted old manifests, `kpi_monitor.py` read the new total (22) and subtracted the old snapshot (97). The resulting negative value (-75) caused the calculated rate to be `-884.9/hr`.
- **Fix:** Deleted `C:\LocalAI_Workstation\config\kpi_state.json`. On the next run, `kpi_monitor.py` will establish a fresh baseline without negative math. The `low_rate` issue only resets the quota state anyway, so it was harmless.

### Bug-03: System Out of Memory (OOM) / STATUS_COMMITMENT_LIMIT (0xc000012d)
- **Issue:** The system's virtual memory (Commit Limit) hit 81.1 GB out of 81.7 GB limit. The biggest offenders were `vmmemWSL` (11GB), Chrome (8.6GB), `llama-server` (7.3GB), and `run_workflow.py` (4GB). This caused OpenCV crashes in Formatter (`Insufficient memory`) and prevented Python from spawning new processes (triggering the Windows popup error 0xc000012d).
- **Resolution:** The user is currently rebooting the system and increasing the Windows Page File (Virtual Memory) size to 128 GB. Upon reboot, the system will start fresh with more headroom.

### Bug-04: Watchdog Pending Tasks = 0
- **Issue:** `watchdog.py` reported `待處理任務=0` because its `PENDING_STATUSES` set was missing `"chunked"`.
- **Fix:** Added `"chunked"` to `PENDING_STATUSES` in `watchdog.py`. Now it properly tracks the remaining 50+ chunked tasks.

### 🔑 Startup Commands for the Next Session
```powershell
# 1. Watchdog (Background worker monitor)
cd C:\LocalAI_Workstation; $env:PYTHONUTF8="1"; python scripts\watchdog.py

# 2. Progress Dashboard
cd C:\LocalAI_Workstation; $env:PYTHONUTF8="1"; python scripts\progress_dashboard.py

# 3. KPI Monitor (Every 5 mins)
cd C:\LocalAI_Workstation; $env:PYTHONUTF8="1"; while ($true) { python scripts\kpi_monitor.py; Start-Sleep -Seconds 300 }
```
