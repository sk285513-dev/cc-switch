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
當前: 49 把金鑰，日配額上限 980 次
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
- **當前緩解**：49把金鑰輪替池，日配額980次。
- **根本解法**：申請 Gemini API 付費方案或蒸餾微調本地14B模型。

### 2. Ollama IPv6 衝突 (已修復 2026-07-09)
- **修復**：`agent_core_pro.py` 全部改為 `127.0.0.1:11434`。

### 3. 工作流意外停止 (已修復 2026-07-09)
- **修復**：`watchdog.py` + 開機自動啟動 VBS 守護程式，自動清鎖重啟。

### 4. 蒸餾數據只有 3 條
- **進度**：3/5,000（每堂課自動採樣~3條）。
