# LexMind-Omni 系統架構完整規劃報告 v5.0
> 更新時間：2026-07-09 ｜ 整合來源：旗艦技術文件 v3.0 + 實作歷史 + 驗收規格書
> 設計原則：積木式堆疊 · 可拆解除錯 · Agent / Skills / MCP 明確分工

---

## 一、七層架構總覽

```
Layer 0  使用者接入層   React/Vite SPA (3000) · Streamlit (8501) · CLI/SDK
Layer 1  API 閘道層    Node.js/Express server.ts (3000) · FastAPI (8080)
Layer 2  協調器層      LocalLegalAgent · LangGraph DAG · RWS 加權
Layer 3  九大 Agent   業務邏輯核心（見第二章）
Layer 3b 轉錄管線     影音全自動轉錄（見第三章）
Layer 4  品質閘門      Legal Eval Gates 七維度（見第五章）
Layer 5  AI 推理層    GPU-0 Ollama · GPU-1 ChromaDB+Whisper
Layer 6  資料持久層   ChromaDB · PostgreSQL · Redis · A:\\ JSON
守護層   MCP 模組     QuotaManager · SystemGuard · SingleInstanceLock
```

---

## 二、九大 Agent 完整規格

### 2.1 Agent 總覽矩陣

| # | Agent 名稱 | 類型 | 主程式 | 類別 | 核心函式 | API 端點 |
|---|-----------|------|--------|------|---------|---------|
| ① | 糾錯排版 | 獨立 | `scripts/agent_core_pro.py` | `LegalProofer` | `format_legal_doc()` | POST `/api/v1/briefs/format` |
| ② | 磁碟掃描 | 獨立 | `scripts/auto_ingest_bot.py` | `LocalMediaScanner` | `scan_local_media()` | GET `/api/scan-local-media` |
| ③ | 網頁爬蟲 | 獨立 | `scripts/web_scraper.py` | `LegalWebScraper` | `scrape_legal_url()` | POST `/api/trigger-scraper` |
| ④ | 期限審查 | 獨立 | `scripts/agent_core_pro.py` | `DeadlineCalendar` | `calculate_limitation()` | POST `/api/v1/timeline/calculate` |
| ⑤ | 考試培訓 | 獨立 | `scripts/exam_agent.py` | `MockExamTrainer` | `generate_exam()` | POST `/api/v1/exam/generate` |
| ⑥ | 知識庫索引 | 協同 | `scripts/auto_ingest_bot.py` | `KnowledgeSynthesizer` | `ingest_to_chroma()` | POST `/api/parse-local-file` |
| ⑦ | 案件主控 | 協同 | `scripts/agent_core_pro.py` | `CaseOrchestrator` | `manage_case()` | GET/POST `/api/cases` |
| ⑧ | RAG 諮詢 | 協同 | `app.py` + `agent_core_pro.py` | `RAGLegalConsult` | `rag_query()` | POST `/api/v1/legal/query` |
| ⑨ | 書狀生成 | 協同 | `scripts/agent_core_pro.py` | `PleadingsDrafter` | `draft_pleading()` | POST `/api/v1/briefs/generate` |

### 2.2 關鍵實作細節

**Agent ① 糾錯排版**
- 正規表達式驗證臺灣法條格式：`[\u4e00-\u9fff]{2,20}(?:法|條例|規則|辦法)第\s*(\d+(?:-\d+)?)\s*條`
- Ollama DeepSeek-R1:7b (GPU-0) 錯字校正
- Hard Gate 閾值：引用準確率 ≥ 0.95

**Agent ④ 期限審查**
- 直接查詢 `src/legal_kb/limitation_periods.py` 知識庫（禁止 LLM 自行計算）
- 零容忍：Hard Gate 閾值 = 1.00
- RWS 時效關鍵字觸發：「消滅時效」「除斥期間」「追訴權時效」「罹於時效」

**Agent ⑧ RAG 諮詢**
- Agentic RAG：`_plan_retrieval()` → 最多 3 輪混合搜尋
- Dense 向量（ChromaDB GPU-1，weight=0.7）+ BM25（weight=0.3）+ RRF（k=60）
- NDCG@5 < 0.7 → 自動重新措辭查詢

---

## 三、影音轉錄管線 Agents（本系統核心）

| Agent | 腳本 | 輸入 → 輸出 | 關鍵規格 |
|-------|------|-----------|---------|
| 👁️ FileWatcher | `file_watcher.py` | J:\\ MP4 → `A:\manifests\task_*.json` | 零拷貝、SHA-256去重、`[課名]_`前綴 |
| 🎥 VisualAnalyzer | `visual_analyzer.py` | J:\\ MP4 → `blackboard\*.jpg` | OpenCV 幀差法 1fps、Gemini OCR板書 |
| 🔧 Preprocess | `preprocess_media.py` | manifest → `extracted_audio.wav` | FFmpeg 16kHz 單聲道 |
| ✂️ ChunkPlanner | `chunk_planner.py` | WAV → `chunk_NNN.wav` (≤12min) | 靜音偵測 >1.5s/-35dB、2GB防護 |
| 🎙️ STT Agent | `stt_runner.py` | chunk WAV → `chunk.txt+.json` | Gemini 2.5 Flash、QuotaManager管429 |
| 🧪 DistillEngine | `stt_runner.py`（內嵌） | Gemini結果 → `distillation_pairs.jsonl` | Whisper medium CPU int8、目標5,000條 |
| 🔗 Merge Agent | `merge_transcript.py` | chunk.txt + 板書 → 完整逐字稿 | 上限1,000,000字、Gemini 2.5 Pro接縫 |
| 📝 Formatter Agent | `markdown_formatter.py` | 完整逐字稿 → 5個成果檔 | Step9 J槽備份、Step10蒸餾採樣 |

### 轉錄 Workflow 流程

```
J:\\ 影音
  └→ [FileWatcher] manifest（零拷貝）
       └→ [Preprocess] FFmpeg → 16kHz WAV
            └→ [ChunkPlanner] 靜音切片 ≤12min
                 └→ [STT Agent] Gemini 2.5 Flash 轉錄
                      ├→ 每片完成立即存檔（斷點續跑）
                      ├→ 429 → QuotaManager 自動退避+金鑰輪替
                      └→ 副線程 [DistillEngine] Whisper CPU對照
  └→ [VisualAnalyzer] OpenCV板書偵測 → Gemini OCR
       └→ [Merge Agent] 接縫精校 + 板書嵌入（時戳對齊）
            └→ [Formatter Agent]
                 ├→ Step 1~8: 大綱/爭點/標題/法條格式化
                 ├→ Step 9: J:\\ 備份（5個成果檔）
                 └→ Step 10: 蒸餾採樣
                      └→ A:\processed_md\[課程名稱].md/.srt/.vtt/.txt/_index.json
```

---

## 四、十八個 Skills 完整清單

### 4.1 v3.0 定義的 18 個核心 Skills

| # | Skill 名稱 | 類別 | 觸發條件 | 對應程式碼 | 狀態 |
|---|-----------|------|---------|-----------|------|
| S01 | `legal-citation-check` | 法律品質 | 法律文本輸出前 | `eval/citation_hallucination.py::CitationAccuracyEvaluator` | ✅ |
| S02 | `hallucination-guard` | 法律品質 | LLM 生成後 | `eval/citation_hallucination.py::HallucinationRateEvaluator` | ✅ |
| S03 | `limitation-calculator` | 法律品質 | 命中時效關鍵字 | `agent_core_pro.py::DeadlineCalendar` | ✅ |
| S04 | `rws-weight-engine` | 法律品質 | 所有 RAG 查詢前 | `agent_core_pro.py::rws_weight()` | ✅ |
| S05 | `brief-formatter` | 文書處理 | 書狀生成後 | `agent_core_pro.py::LegalProofer` | ✅ |
| S06 | `court-style-validator` | 文書處理 | 書狀輸出前 | `eval/statute_format_retrieval.py` | ✅ |
| S07 | `whisper-transcribe` | 多模態 | 音視頻輸入 | `auto_ingest_bot.py::process_audio_video` | ✅ |
| S08 | `pdf-ocr-extract` | 多模態 | PDF 輸入 | `auto_ingest_bot.py::process_pdf` | ✅ |
| S09 | `legal-web-scrape` | 資料採集 | 爬蟲任務觸發 | `web_scraper.py::LegalWebScraper` | ⏳ |
| S10 | `exam-question-parse` | 資料採集 | 考題爬取任務 | `exam_agent.py::crawl_past_exams` | ⏳ |
| S11 | `hybrid-search` | 向量檢索 | RAG 查詢執行 | `src/vector/hybrid_search.py` | ✅ |
| S12 | `chroma-upsert` | 向量檢索 | 教材吸收完成 | `auto_ingest_bot.py::upsert_vector` | ✅ |
| S13 | `hnsw-index-tune` | 向量檢索 | 索引效能退化 | `src/vector/index_benchmark.py` | ⏳ |
| S14 | `eval-gate-runner` | CI/CD | PR 合併前 | `eval/run_eval_gates.py` | ⏳ |
| S15 | `deploy-guard` | CI/CD | 部署前驗證 | `eval/deploy_guard.py` | ⏳ |
| S16 | `oom-circuit-breaker` | 系統防護 | 記憶體 >85% | `config_loader.py::cleanup_memory` | ✅ |
| S17 | `chroma-singleton` | 系統防護 | ChromaDB 初始化 | `agent_core_pro.py::get_chroma_client` | ✅ |
| S18 | `git-rollback-protocol` | 系統防護 | 連續3輪除錯失敗 | CLAUDE.md 協議 | ✅ |

### 4.2 本專案轉錄管線新增 Skills

| Skill | 觸發場景 | 對應 Agent |
|-------|---------|-----------|
| `multimodal-transcriber` | STT 參數/Whisper 詞彙表 | STT Agent |
| `visual-blackboard-analyzer` | OpenCV閾值/Mermaid模板 | VisualAnalyzer |
| `knowledge-deep-digester` | 摘要格式調整 | Merge Agent |
| `mapreduce-corrector` | 大文本分塊精校 | Merge Agent |
| `gpu-parallel-orchestrator` | 雙 GPU 排程/動態並發 | QLoRA Trainer |
| `system-guard-watchdog` | 資源監控閾值 | SystemGuard MCP |
| `rag-case-consultant` | RAG 權重/法律問答邏輯 | LocalLegalAgent |
| `exam-adversarial-trainer` | 考題生成/答案評分 | Evaluator Agent |
| `statute-limitations-expert` | 時效計算規則 | LocalLegalAgent |
| `auto-ingestion-guard` | 掃描路徑/格式過濾 | FileWatcher |
| `secure-vault-backup` | 加密備份/金鑰管理 | Formatter Agent |
| `law-scraper-validator` | 法規爬蟲網域/關鍵字 | RAG Ingest Agent |

---

## 五、Legal Eval Gates 品質閘門

### 5.1 七維度閘門矩陣

| 閘門 | 類型 | 閾值 | 失敗行為 | 程式碼 |
|------|------|------|---------|--------|
| 法條引用準確性 | **Hard** | ≥ 0.95（生產 ≥ 0.97） | Block PR | `citation_hallucination.py` |
| 幻覺率 | **Hard** | < 0.05（生產 < 0.03） | Block PR | `citation_hallucination.py` |
| 時效計算正確性 | **Hard** | = 1.00（零容忍） | Block PR | `statute_format_retrieval.py` |
| 回應延遲 P95 | **Hard** | < 3000ms（生產 < 2000ms） | Block PR | `latency_idempotency.py` |
| 冪等性 | **Hard** | = 1.00 | Block PR | `latency_idempotency.py` |
| 書狀格式合規 | Soft | ≥ 0.85 | Warn | `statute_format_retrieval.py` |
| NDCG@5 | Soft | ≥ 0.80 | Warn | `eval_gates.py` |
| **綜合分數** | Composite | **≥ 0.88** | Block Deploy | `eval_gates.py` |

### 5.2 法律內容品質驗收標準（驗收規格書）

| 項目 | 標準 |
|------|------|
| 贅字過濾 | 100%（那個/然後/就是說/嗯/啊 全清除） |
| 同音錯字正確率 | ≥ 98%（地政士≠遞贈式、消滅時效≠消滅實效） |
| 法條格式 | 民法第197條 / 行政程序法第131條 |
| 字號格式 | 釋字第474號解釋 / 最高法院49年台上字第1730號 |
| Markdown 結構 | 自動分層(#/##/###) + 粗體標記 `**【爭點】**` |

---

## 六、守護層 MCP 模組

### 🔑 QuotaManager MCP
```yaml
路徑: scripts/quota_manager.py
介面:
  acquire_key()              # 取得可用金鑰
  handle_error(e,key,count)  # 429精確秒數cold down + 輪替
  mark_exhausted(key)        # 標記耗盡
  _save_state()              # 持久化 config/quota_state.json
退避策略:
  連續3次 429 → 換下一把金鑰
  全部耗盡    → 300s 冷卻 → reset_all_keys()
  蒸餾引擎   → 強制 CPU-only int8（防 mkl_malloc OOM）
金鑰儲存: config/secure_keys.vault (Fernet 加密的 JSON Array)
配額計算: 動態依據 Vault 內的有效金鑰數量計算 (每把金鑰每日 20 次)。
         (舉例：若有 49 把金鑰，日配額上限即為 980 次；若為 39 把，則為 780 次)
```

### 🛡️ SystemGuard MCP
```yaml
技能: system-guard-watchdog SKILL
監控: GPU溫度(≤78°C) · VRAM · A:\空間(<50GB告警) · RAM
頻率: 每15秒
行動: 超溫→暫停→降溫→恢復 / OOM→三級降級(float16→float32→CPU)
```

### 🔒 SingleInstanceLock + Watchdog 守護
```yaml
SingleInstanceLock: run_workflow.py msvcrt互斥鎖
  優先順序: 憲法=0 > mock=5 > 民刑行=10 > 民訴=20 > 地政=30 > 商=40 > 其他=50
  遞迴消化: 持鎖直到佇列清空

Watchdog (NEW 2026-07-09):
  腳本: scripts/watchdog.py
  開機啟動: Startup\LexMind-Watchdog.vbs（登入自動執行）
  邏輯: 每60s檢查 → 進程死/日誌10min停滯 → 自動重啟
  日誌: A:\logs\watchdog.log
```

---

## 七、當前遭遇問題 × 達成辦法

### 1. API 429 限速
- **當前緩解**：使用 QuotaManager 建立多金鑰輪替池，依據動態載入的有效金鑰數量擴充日配額（舉例：若匯入 39 把有效金鑰，日配額即擴張為 780 次）。
- **根本解法**：申請 Gemini API 付費方案或蒸餾微調本地14B模型。

### 2. Ollama IPv6 衝突 (已修復 2026-07-09)
- **修復**：`agent_core_pro.py` 全部改為 `127.0.0.1:11434`。

### 3. 工作流意外停止 (已修復 2026-07-09)
- **修復**：`watchdog.py` + 開機自動啟動 VBS 守護程式，自動清鎖重啟。

### 4. 蒸餾數據累積過慢
- **問題描述**：系統初期設定每堂課僅自動採樣極少數對齊資料，導致初期查閱時進度緩慢（例如初期僅有 3 條）。
- **解決方案**：資料會隨著系統持續消化課程而自動累積（目標 5,000 條），後續可視需求於腳本中調整抽樣率。

---

## 八、2026-07-24 重大穩定度修復 (System Stability Fixes)

本次修復針對舊有架構 (`C:\LocalAI_Workstation`) 遷移至新架構 (`C:\New_LocalAI_Workstation`) 時發生的一系列「系統崩潰」、「進程死鎖」與「API 金鑰耗盡假象」進行了深度清理與修正。

### 1. Gemini SDK v1.0 升級導致的 `_api_key` 崩潰
* **問題描述**：舊版 STT Agent 在遭遇 429 速率限制並由 QuotaManager 替換金鑰後，會試圖比對 `upload_client._api_key != active_key`。但在新版 `google-genai` SDK v1.0 中，`Client` 物件移除了 `_api_key` 屬性，導致引發 `AttributeError: 'Client' object has no attribute '_api_key'` 並造成工作流中斷。
* **舊版程式碼 (`scripts/stt_runner.py`)**：
  ```python
  if upload_client is not None and upload_client._api_key != active_key:
      # 刪除舊檔案...
  ```
* **新版程式碼 (`scripts/stt_runner.py`)**：
  ```python
  if upload_client is not None and getattr(getattr(upload_client, "_api_client", None), "api_key", None) != active_key:
      # 刪除舊檔案...
  ```
* **影響**：修復後，在 STT 階段遇到 429 時能平滑切換 API 金鑰，不會再中斷進程。

### 2. QuotaManager 處理 429 限制的參數錯字
* **問題描述**：當 `merge_transcript.py` 遭遇 429 錯誤時，試圖呼叫 `QuotaManager.handle_error()`，但傳入了錯誤的關鍵字參數名稱，導致觸發 `TypeError`，破壞了金鑰輪替機制。
* **舊版程式碼 (`scripts/merge_transcript.py`)**：
  ```python
  active_key = quota_manager.handle_error(e, active_key, consecutive_429_count=consecutive_429)
  ```
* **新版程式碼 (`scripts/merge_transcript.py`)**：
  ```python
  active_key = quota_manager.handle_error(e, active_key, consecutive_429=consecutive_429)
  ```

### 3. 多進程日誌鎖定導致 PermissionError (WinError 32)
* **問題描述**：舊版在 `scripts/workflow_helper.py` 中使用了 `RotatingFileHandler`。在 Windows 作業系統中，當多個 Agent 併發執行並試圖同時旋轉（Rotate）`A:\logs\workflow.log` 檔案時，會引發檔案權限互鎖（WinError 32），直接導致背景工作崩潰。
* **舊版程式碼 (`scripts/workflow_helper.py`)**：
  ```python
  from logging.handlers import RotatingFileHandler
  handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
  ```
* **新版程式碼 (`scripts/workflow_helper.py`)**：
  ```python
  handler = logging.FileHandler(log_file, encoding="utf-8")
  ```

### 4. 舊環境幽靈進程與金鑰死鎖清理
* **問題描述**：使用者雖然切換至 `C:\New_LocalAI_Workstation`，但舊目錄 (`C:\LocalAI_Workstation`) 下仍有多個 `watchdog.py` 與 `run_workflow.py` 在背景執行，這些幽靈進程不僅爭奪有限的 API 金鑰，更在崩潰時將金鑰遺留在 `quota_state.json` 的 `in_use_keys` 陣列中，導致系統誤判「所有金鑰均已被佔用或耗盡」。
* **修復動作**：
  1. 使用 Taskkill 強制終止舊路徑下所有殘留的 `pythonw.exe` 與 `powershell.exe`。
  2. 手動清空 `C:\New_LocalAI_Workstation\config\quota_state.json` 的內部狀態：
     ```json
     {"exhausted_keys": [], "in_use_keys": []}
     ```
  3. 將 `config.yaml` 內的 `stt_engine` 正確設定回 `"gemini"`。

---

## 九、高併發視覺測試與 26 項穩定性機制總結
> 彙整自《基於涵蓋陣列與 DOM 狀態感知之高併發法律系統自動化視覺測試框架設計與實作》

本系統在開發與測試階段，針對前端 DOM 狀態、併發資源與 AI 穩定性等挑戰，實作了以下 26 項核心除錯與防禦機制：

- **機制一：實體會話突破機制之設計 (Session 0 Breakthrough via VBS Isolation)**： 問題源頭 (Problem Definition)： 當自動化爬蟲被 AI Agent (如 Antigravity 沙箱) 或 Windows 背景排程器 ...
- **機制二：強制防護等待之設計 (Event-Driven DOM Synchronization)**： 問題源頭 (Problem Definition)： 傳統自動化腳本大量依賴靜態休眠 (`time.sleep`)。然而，Streamlit 基於 WebSo...
- **機制三：崩潰紅字防禦之設計 (Implicit Dynamic Oracles)**： 問題源頭 (Problem Definition)： 當 Python 後端處理超載或遭遇未捕捉的例外 (Unhandled Exception) 時，Str...
- **機制四：絕對畫面捕捉與死碼消除之設計 (Resource Acquisition Is Initialization, RAII)**： 問題源頭 (Problem Definition)： 在過往的腳本迭代中，我們發現大量的快照截圖邏輯被錯誤地放置在與異常處理同層的控制流中。當 `try` 區...
- **機制五：空間感知遍歷之設計 (Semantic DOM Traversal)**： 問題源頭 (Problem Definition)： 傳統的網頁爬蟲大多依賴 URL 進行導航 (Navigationbased Crawling)。然而對於...
- **機制六：全面實體留存與 OOM 迴避之設計 (Disk I/O Isolation)**： 問題源頭 (Problem Definition)： 在過往設計中，開發者常將截圖以 Base64 編碼字串的形式保存在 Python 變數或直接印出至對話日...
- **機制七：語意與測試解耦之設計 (Semantic Assertion Decoupling)**： 問題源頭 (Problem Definition)： 傳統的自動化腳本習慣在程式碼中寫死斷言 (例如 `assert "勝訴" in page_text`)。...
- **機制八：防組合爆炸演算法之設計 (Combinatorial Explosion Prevention)**： 問題源頭 (Problem Definition)： 系統畫面上若存在多達 67 個 Checkbox（如各種法律爭點的開關），若使用暴力窮舉 (Brutef...
- **機制九：多維度隱藏元件探索之設計 (Hidden Element Exploration)**： 問題源頭 (Problem Definition)： 現代 SPA 為了版面簡潔，大量使用摺疊面板 (Accordion/Expander)、模態對話框 (M...
- **機制十：真值表軌跡追蹤之設計 (Statechart Traceability Logging)**： 問題源頭 (Problem Definition)： 當事後檢閱崩潰截圖時，開發者往往只能看到一個錯誤畫面，卻無從得知導致該崩潰的「因」——也就是在崩潰前一刻...
- **機制十一：核心分頁狀態重置之設計 (Forced State Reset)**： 問題源頭 (Problem Definition)： 連續注入 600 個案例時，前一個案例可能引發了錯誤的錯誤訊息彈窗、或將頁面導向了其他子系統，導致下一個...
- **機制十二：高擬真事件注入之設計 (High-Fidelity Synthetic Events)**： 問題源頭 (Problem Definition)： 單純地使用 JavaScript 賦值 (如 `element.value = "..."`) 雖然能改...
- **機制十三：動態非同步推論等待與驗證之設計 (Async Spinner Synchronization & Backend Validation)**： 問題源頭 (Problem Definition)： 後端呼叫 Gemini 或其他 LLM 進行推論時，耗時從 5 秒到 60 秒不等，具有極大的方差。若寫...
- **機制十四：硬體級 Watchdog 與 Email 警報之設計 (Deadlock Watchdog)**： 問題源頭 (Problem Definition)： `workflow_helper.py` 遭受語法修改 (IndentationError) 導致管線守...
- **機制十五：時鐘同步與分散式排程校正之設計 (Timezone & Priority Queue)**： 問題源頭 (Problem Definition)： `datetime.now()` 在遠端伺服器抓取至 UTC 時間，使排程器誤判非執行時段，鎖死 345...
- **機制十六：非同步進程解耦與 UI 阻塞防禦之設計 (Daemonization Decoupling)**： 問題源頭 (Problem Definition)： 當 AI Agent 透過 `python script.py` 啟動無窮迴圈的常駐程式時，終端機管道 ...
- **機制十七：異質計算 OOM 記憶體爭用隔離之設計 (Memory Page Swap Defense)**： 問題源頭 (Problem Definition)： 大模型 (llamaserver) 與視覺處理 (OpenCV) 並行時，虛擬記憶體飆破 81.1GB，...
- **機制十八：429 金鑰輪替與 API 退避容錯之設計 (API Backoff Resiliency)**： 問題源頭 (Problem Definition)： 高併發 STT 請求導致 Gemini API 短時間內觸發 `429 Too Many Request...
- **機制十九：全鏈路資源遙測與效能指紋之設計 (Full-Stack Resource Telemetry)**： 問題源頭 (Problem Definition)： 在長時間運作的視覺測試框架中，系統常遭遇未知的效能瓶頸與記憶體緩步洩漏 (Memory Leak)，但因...
- **機制二十：多維度錯誤熱力圖與特徵關聯之設計 (Multidimensional Error Heatmap Analysis)**： 問題源頭 (Problem Definition)： 在組合爆炸測試中，系統可能產生高達 600 筆 JSON 數據。當其中數十筆觸發崩潰時，人眼與傳統分析工...
- **機制二十一：AI 幻覺失控防禦與上下文持續性邊界約束之設計 (AI Hallucination Defense)**： 問題源頭 (Problem Definition)： 在建構高併發自動化測試與管線開發期間，大語言模型 (LLM/AI Agent) 反覆發生「自我幻覺 (H...
- **機制二十二：代理人紀律引擎與 Markdown 解析器防護之設計 (Agent Discipline Engine)**： 問題源頭 (Problem Definition)： AI 在輸出 Markdown 報告時，經常忽略 Obsidian 等軟體的嚴格縮排要求（例如列表內嵌 ...
- **機制二十三：跨進程編碼統一與作業系統 Pipe 崩潰防禦 (Unicode Encoding Enforcement)**： 問題源頭 (Problem Definition)： 在處理繁體中文法律字彙與特殊符號時，Windows 終端機預設使用 `cp950` (Big5) 編碼。...
- **機制二十四：本地端網路協定衝突解析與 IPv6 繞道機制 (IPv6 Resolution Bypass)**： 問題源頭 (Problem Definition)： LocalLegalAgent 在呼叫本地端 Ollama 服務時，由於 Windows 11 的 DN...
- **機制二十五：異步硬體資源調度與 CPU 離線分片機制 (Asynchronous CPU Chunking)**： 問題源頭 (Problem Definition)： 處理單堂 2.6 小時巨型影音檔時，若音訊提取、切片與 GPU 轉寫同步進行，會引發 CPU 100% ...
- **機制二十六：雙軌蒸餾採樣與本地端 AI 模型降維微調策略 (Dual-Track Distillation Sampling)**： 問題源頭 (Problem Definition)： 本機端的開源 Whisper 模型對台灣法律專有名詞辨識度極低（常將「各論」誤植為「格論」），但長期依賴...
