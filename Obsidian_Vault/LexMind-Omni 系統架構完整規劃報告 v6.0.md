# LexMind-Omni 系統架構完整規劃報告 v6.0
> 更新時間：2026-07-24 ｜ 整合來源：v5.0 架構、視覺測試論文、SRE 優化紀實
> 設計原則：積木式堆疊 · 可拆解除錯 · Agent / Skills / MCP 明確分工 · 高併發容錯

## 1. 七層架構總覽 (Layered Architecture)
LexMind-Omni 採用七層解耦架構，確保前端展示、業務邏輯與底層運算資源分離：
- **Layer 0 使用者接入層**: React/Vite SPA (Port 3000) · Streamlit (Port 8501) · CLI/SDK
- **Layer 1 API 閘道層**: Node.js/Express `server.ts` (Port 3000) · FastAPI (Port 8080)
- **Layer 2 協調器層**: LocalLegalAgent · LangGraph DAG · RWS 加權引擎
- **Layer 3 核心 Agent**: 九大業務邏輯核心 Agent (詳見第二章)
- **Layer 3b 轉錄管線**: 影音全自動多模態轉錄管線 (詳見第四章)
- **Layer 4 品質閘門**: Legal Eval Gates 七維度評估與雙軌蒸餾 (詳見第六章)
- **Layer 5 AI 推理層**: GPU-0 (Ollama DeepSeek-R1:7b) · GPU-1 (ChromaDB + Whisper)
- **Layer 6 資料持久層**: ChromaDB 向量庫 · PostgreSQL · KernelMutex IPC · `A:\` JSON 狀態暫存
- **守護層 MCP 模組**: QuotaManager · SystemGuard · SingleInstanceLock · 系統級 Watchdog

## 2. 核心 Agent 與視覺測試引擎 (Core Agents & Visual Testing Engine)
### 2.1 九大核心 Agent
| Agent | 類別 | 核心功能 |
|---|---|---|
| ① 糾錯排版 | `LegalProofer` | 正規表達式驗證法條格式、Ollama 錯字校正 (要求 ≥ 0.95 準確率) |
| ② 磁碟掃描 | `LocalMediaScanner` | 掃描本地影音與 PDF 文件，觸發管線 |
| ③ 網頁爬蟲 | `LegalWebScraper` | 採集外部法學資料 |
| ④ 期限審查 | `DeadlineCalendar` | 時效關鍵字觸發計算，直接查詢知識庫，嚴禁 LLM 幻覺 (閾值 1.00) |
| ⑤ 考試培訓 | `MockExamTrainer` | 歷屆考題生成與對練 |
| ⑥ 知識庫索引 | `KnowledgeSynthesizer` | 吸收教材，寫入 ChromaDB 向量庫 |
| ⑦ 案件主控 | `CaseOrchestrator` | 總管案件狀態流轉 |
| ⑧ RAG 諮詢 | `RAGLegalConsult` | Agentic RAG，混合搜尋 (Dense+BM25+RRF)，動態改寫查詢 |
| ⑨ 書狀生成 | `PleadingsDrafter` | 依據法庭合規格式生成書狀 |

### 2.2 視覺測試引擎 (Visual Testing Engine)
基於 Playwright 與事件驅動 (Event-Driven) 打造的高併發 GUI 測試引擎。摒棄傳統 `time.sleep`，導入 Chrome DevTools Protocol (CDP) 監聽 DOM MutationObserver 實現精準同步；採用涵蓋陣列 (Covering Arrays) 防止組合爆炸；並透過隱式動態神諭 (Implicit Dynamic Oracles) 與 RAII (Resource Acquisition Is Initialization) 哲學，確保 OOM 隔離及 100% 決定性快照，實現自動化視覺評測。


## 2.5 設定總欄金鑰管理 UI (Settings View)
【歷史教訓防呆宣告】：本系統之金鑰管理 UI 位於 `components/settings_view.py`。任何 AI 開發者接手修改 QuotaManager、Vault 等底層架構時，**絕對禁止**捨棄、破壞或閹割以下三大核心 GUI 功能：
1. **📊 視覺化戰情看板 (Visual Dashboard)**：直觀顯示（總數、有效啟用中、失效停用）三項指標儀表板，提供彈藥庫存狀態。
2. **📥 無腦批次匯入區 (Smart Batch Importer)**：提供大型文字框，支援無腦貼上大量亂碼，系統需自動解析、剔除重複項並與現有表格合併，禁止重複加入。
3. **🧪 主動式 API 狀態檢測儀 (Active API Tester)**：背景自動敲擊 API 檢測 200/403/429。遇到 403 停權時，必須打上🔴標記並**自動將該金鑰的 active 狀態切換為 False**，阻絕壞金鑰進入後端排隊池。

若遺失上述功能，應立即從 `C:\LocalAI_Workstation\components\settings_view.py` 舊備份中還原，禁止自行重造純後端輪子。


### 2.5.1 設定總欄 UI 與後端引擎的安全銜接架構
為避免 UI 介面與背景轉錄 Worker 發生資源衝突或觸發 API 封鎖，`settings_view.py` 的實作必須嚴格遵守以下三大防護機制：
1. **跨行程寫入鎖 (Cross-Process File Lock)**：在執行「批次匯入」或「一鍵清除」導致金鑰變動時，寫入 `config/secure_keys.vault` 的動作必須由 `FileLock` 保護，避免與 `QuotaManager` 的輪替機制發生 Race Condition 導致 Vault 檔案損毀 (0 byte)。
2. **非同步檢測與限速 (Async & Token Bucket)**：「啟動全體金鑰檢測」不可使用阻塞式的 `requests` 迴圈。必須採用非同步設計，並加入每秒 2~3 把的限速，防止 Streamlit UI 卡死或因短時間大量戳 API 而遭 Google WAF 429 封鎖（封鎖風暴）。
3. **狀態機 IPC 同步**：當 UI 將 403 金鑰標記為失效 (`active=False`) 後，必須即時更新或觸發 `config/quota_state.json` 重置，強制背景所有 Worker 重新載入金鑰池，避免 Worker 繼續使用失效金鑰。
4. **SRE QoS 測試流量隔離 (Quality of Service) [解決 Issue 11]**：API Gateway 必須識別 `X-Test-Traffic: 1` 標頭。自動化視覺測試等機器人流量，必須被路由至專屬的金鑰池 (`secure_keys_test.vault`)，且並發佇列排程優先權強制低於生產環境 (Production Workloads)，嚴防測試流量耗盡全域 Token Bucket 而導致正常用戶被 429 拒絕服務。
5. **地端資安與記憶體零化機制 (Memory Zeroing) [解決 Issue 12, 13]**：僅加密硬碟檔案是不夠的。針對記憶體明文洩漏防護，載入 API 金鑰至 RAM 時，強制使用 Python `bytearray` (而非 Immutable Strings)。當請求結束或金鑰失效時，必須立即呼叫 `ctypes.memset(id(key_buffer), 0, len)` 直接對記憶體位址進行覆寫歸零，防堵 JIT 優化殘留與記憶體傾印 (Memory Dump) 攻擊。

## 3. 高併發分散式 API 金鑰排程與流量控制架構 (Key Management Engine)
針對 Gemini 等雲端 AI 的 `429 Too Many Requests` 與配額耗盡問題，設計了全域的 `QuotaManager`：
- **動態配額計算**: 讀取 `config/secure_keys.vault` 內加密金鑰。系統會依據有效金鑰數量動態擴張每日配額（如 39 把有效金鑰，即自動提供 780 次/日 上限）。
- **退避策略與金鑰輪替**:
  - 連續 3 次遭 429 降速，自動切換至下一把有效金鑰。
  - 當捕獲 429 HTTPStatusError，精確解析 `retry-after` 進行抖動指數退避 (Exponential Backoff with Jitter)，防止重試風暴 (Thundering Herd)。
  - 若所有金鑰耗盡，全域進入 300 秒冷卻期，隨後呼叫 `reset_all_keys()`。
- **跨進程同步**: 使用 `config/quota_state.json` 作為狀態機，確保分散式 Agent (如多個 `stt_runner`) 不會發生金鑰競爭與死鎖。

## 4. 高併發影音轉錄管線 (High-Concurrency Pipeline)
專為大型法律課程影音設計，全程自動化與非同步處理：
1. **FileWatcher**: 零拷貝掃描 `J:\` MP4 檔案，生成 Manifest。
2. **VisualAnalyzer**: OpenCV 幀差法 (1fps) 偵測板書，Gemini 進行 OCR 辨識。
3. **Preprocess**: FFmpeg 抽取 16kHz 單聲道 WAV。
4. **ChunkPlanner**: 靜音偵測 (>-35dB, 1.5s) 智慧切片，單檔 ≤12min，具備 2GB 記憶體防護。
5. **STT Agent**: Gemini 2.5 Flash 平行轉錄，結合 QuotaManager 進行限流防禦。
6. **DistillEngine**: 副線程使用 Whisper medium CPU (int8) 進行雙軌比對。
7. **Merge Agent**: 處理 100 萬字級別的文本接縫，並進行時戳對齊與板書嵌入。
8. **Formatter Agent**: 大綱/爭點/法條格式化，最終輸出 Markdown/SRT/VTT 檔案。

## 5. Skills 模組完整清單 (Skills Inventory)
系統包含 18+ 項核心 Skills：
- **法律與品質 (Quality)**: `legal-citation-check`, `hallucination-guard`, `limitation-calculator`, `rws-weight-engine`
- **文書與處理 (Document)**: `brief-formatter`, `court-style-validator`
- **多模態與採集 (Multimodal & Scrape)**: `whisper-transcribe`, `pdf-ocr-extract`, `legal-web-scrape`, `exam-question-parse`
- **檢索與索引 (Retrieval)**: `hybrid-search`, `chroma-upsert`, `hnsw-index-tune`
- **防護與維運 (Ops & Guard)**: `eval-gate-runner`, `deploy-guard`, `oom-circuit-breaker`, `chroma-singleton`, `git-rollback-protocol`
- **轉錄管線專屬 (Pipeline)**: `multimodal-transcriber`, `visual-blackboard-analyzer`, `knowledge-deep-digester`, `mapreduce-corrector`, `gpu-parallel-orchestrator`, `system-guard-watchdog`, `rag-case-consultant`, `exam-adversarial-trainer`, `statute-limitations-expert`, `auto-ingestion-guard`, `secure-vault-backup`, `law-scraper-validator`

## 6. Legal Eval Gates 品質閘門與雙軌蒸餾 (Quality Gates & Distillation)
### 6.1 七維度品質閘門
部署前必須通過的嚴格測試矩陣：
- **Hard Gates (Block PR)**: 法條引用準確性 (≥ 0.95)、幻覺率 (< 0.05)、時效計算正確性 (1.00 零容忍)、回應延遲 P95 (< 3000ms)、冪等性 (1.00)。
- **Soft Gates (Warn)**: 書狀格式合規 (≥ 0.85)、NDCG@5 (≥ 0.80)。
- **綜合要求**: Composite Score ≥ 0.88 方可發佈。
### 6.2 雙軌蒸餾 (Dual-Track Distillation)
因開源 Whisper 對台灣法律專有名詞 (如「各論」) 辨識不佳，系統內建 DistillEngine，以 Gemini 2.5 Flash 的高精度輸出作為 Teacher，Whisper CPU int8 的輸出作為 Student，持續採集錯字與對齊標籤。目標累積 5,000 條高價值蒸餾資料 (Distillation Pairs) 供後續本地 LLM 降維微調使用。

## 7. 守護層 MCP 模組與 SRE 可靠性 (Daemon & SRE)
基於 Google SRE 實踐設計的底層防護：
- **SystemGuard**: `system-guard-watchdog` 每 15 秒監測 GPU 溫度 (≤78°C)、VRAM、RAM 與硬碟空間。超溫自動降載，OOM 執行三級降級 (float16 → float32 → CPU)。
- **SingleInstanceLock & 優先權佇列**: 透過 `msvcrt` 互斥鎖確保管線單一實例。實施多階段優先順序 (憲法>民刑>其他)。
- **SRE Watchdog (郵件告警)**: 若管線日誌超過 30 分鐘無更新，繞過軟體邏輯直接觸發 SMTP 警報並嘗試重啟。
- **時鐘同步**: 強制統一使用絕對時間 `utcnow() + timedelta(hours=8)`，消除分散式節點時區誤差。
- **作業系統進程解耦 (Daemonization)**: 代理人啟動常駐程式全面採用 `Start-Process pythonw -WindowStyle Hidden`，避免 STDIN/STDOUT 管道阻塞 UI 介面。

## 8. 高併發視覺測試與 26 項穩定性機制 (26 Stability Mechanisms)
本框架實作了 26 項工程防禦機制以應對單頁應用 (SPA) 與 AI 的非確定性：
1. 實體會話突破機制之設計 (Session 0 Breakthrough via VBS Isolation)
2. 強制防護等待之設計 (Event-Driven DOM Synchronization)
3. 崩潰紅字防禦之設計 (Implicit Dynamic Oracles)
4. 絕對畫面捕捉與死碼消除之設計 (RAII)
5. 空間感知遍歷之設計 (Semantic DOM Traversal)
6. 全面實體留存與 OOM 迴避之設計 (Disk I/O Isolation)
7. 語意與測試解耦之設計 (Semantic Assertion Decoupling)
8. 防組合爆炸演算法之設計 (Combinatorial Explosion Prevention via Covering Arrays)
9. 多維度隱藏元件探索之設計 (Hidden Element Exploration)
10. 真值表軌跡追蹤之設計 (Statechart Traceability Logging)
11. 核心分頁狀態重置之設計 (Forced State Reset)
12. 高擬真事件注入之設計 (High-Fidelity Synthetic Events)
13. 動態非同步推論等待與驗證之設計 (Async Spinner Synchronization)
14. 硬體級 Watchdog 與 Email 警報之設計 (Deadlock Watchdog)
15. 時鐘同步與分散式排程校正之設計 (Timezone & Priority Queue)
16. 非同步進程解耦與 UI 阻塞防禦之設計 (Daemonization Decoupling)
17. 異質計算 OOM 記憶體爭用隔離之設計 (Memory Page Swap Defense)
18. 429 金鑰輪替與 API 退避容錯之設計 (API Backoff Resiliency)
19. 全鏈路資源遙測與效能指紋之設計 (Full-Stack Resource Telemetry)
20. 多維度錯誤熱力圖與特徵關聯之設計 (Multidimensional Error Heatmap Analysis)
21. AI 幻覺失控防禦與上下文持續性邊界約束之設計 (AI Hallucination Defense)
22. 代理人紀律引擎與 Markdown 解析器防護之設計 (Agent Discipline Engine)
23. 跨進程編碼統一與作業系統 Pipe 崩潰防禦 (Unicode Encoding Enforcement)
24. 本地端網路協定衝突解析與 IPv6 繞道機制 (IPv6 Resolution Bypass)
25. 異步硬體資源調度與 CPU 離線分片機制 (Asynchronous CPU Chunking)
26. 雙軌蒸餾採樣與本地端 AI 模型降維微調策略 (Dual-Track Distillation Sampling)

## 9. 系統遷移與重大修復紀實 (Migration & Triage)
記錄由 `C:\LocalAI_Workstation` 遷移至 `C:\New_LocalAI_Workstation` 期間的關鍵修復：
1. **Gemini SDK v1.0 升級崩潰 (`_api_key`)**: 因新版 SDK 移除了 `Client._api_key`，導致 429 輪替時觸發 AttributeError 崩潰。已將檢查邏輯更新為 `getattr(getattr(upload_client, "_api_client", None), "api_key", None)`。
2. **QuotaManager 參數錯字修復**: `scripts/merge_transcript.py` 在呼叫 `handle_error` 時傳入錯誤參數名 (`consecutive_429_count` 改回 `consecutive_429`)，修復金鑰輪替失效。
3. **多進程日誌鎖定 WinError 32**: 移除 `workflow_helper.py` 的 `RotatingFileHandler`，改用單純的 `logging.FileHandler` 避免 Windows 環境下的檔案操作互斥鎖死。
4. **舊環境幽靈進程清理**: 使用 Taskkill 清除殘留的 `watchdog.py`，並重置 `config/quota_state.json` 消除假性金鑰耗盡，確保新工作站資源清空。
5. **記憶體爭用 (0xc000012d)**: 利用 PowerShell 強制設定 Windows Page File 至 128GB，徹底解決 CPU/GPU 滿載時分頁表建立失敗的問題。
