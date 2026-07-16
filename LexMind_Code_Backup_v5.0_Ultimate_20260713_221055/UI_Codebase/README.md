# ⚖️ LexMind-Omni 法律實務 AI 工作站 (v5.0)

本專案為 **LexMind-Omni 法律實務 AI 工作站** 的核心 codebase。旨在針對海量（上千堂、單堂時長約 2.6 小時）的台灣法律課程影音教材，進行全自動的智慧語音轉寫、板書視覺 OCR、全文語意精校與格式化，生成正確率 ≥ 98% 的精美講義與字幕，並建立 RAG 法律檢索知識庫。

---

## 📂 一、 系統七層架構與分工

```
Layer 0  使用者接入層   React/Vite SPA (Port:3000) · Streamlit 對話 UI (Port:8501) · CLI/SDK
Layer 1  API 閘道層    Node.js/Express (server.ts Port:3000) · FastAPI (src/api/main.py Port:8080)
Layer 2  協調器層      LocalLegalAgent (scripts/agent_core_pro.py) · LangGraph DAG · RWS 加權
Layer 3  九大 Agent   ②磁碟掃描 · ③網頁爬蟲 · ⑤考試培訓 · ⑥知識庫索引 · ⑦案件主控 · ⑧RAG諮詢 · ⑨書狀生成等
Layer 3b 轉錄管線     👁️FileWatcher → 🎥VisualAnalyzer → 🔧Preprocess → ✂️ChunkPlanner → 🎙️STT → 🧪Distill → 🔗Merge → 📝Formatter
Layer 4  品質閘門      Legal Eval Gates 七維度評測（法條引用、幻覺率、時效計算、延遲、冪等性）
Layer 5  AI 推理層    GPU-0 (RTX 5060 Ti): Ollama DeepSeek-R1:7b | GPU-1: ChromaDB + Whisper
Layer 6  資料持久層   ChromaDB · PostgreSQL · Redis · A:\\ manifests 與 processed_md 落地目錄
守護層   MCP 模組     QuotaManager (49金鑰) · SystemGuard (溫度防護) · SingleInstanceLock + Watchdog 守護
```

---

## 🎙️ 二、 影音轉錄自動化管線

系統採用 **「本地端重度 I/O + 雲端高階語意理解」** 的雙環分工。所有任務通過 `A:\manifests\task_*.json` 狀態機驅動，實現全自動、零拷貝的流式處理：

```
J:\\ 原始影音 ─┐
              ├→ [FileWatcher] 建立 manifest (實體路徑直讀，不二次複製)
              └→ [Preprocess] FFmpeg 本地降採樣 → 16kHz 單聲道 WAV
                   └→ [ChunkPlanner] 智慧靜音波形偵測切片 (≤ 12 分鐘，重疊 30s)
                        └→ [STT Agent] Gemini 2.5 Flash 雲端轉錄 (自動過濾口語贅字)
                             ├─ 每片完成立即回寫 manifest（支援斷點續跑）
                             ├─ 遇到 429 觸發 QuotaManager 金鑰池輪替
                             └─ 同步觸發 [DistillEngine] Whisper CPU 本地轉寫生成蒸餾對
  J:\\ MP4 ───┐
              └→ [VisualAnalyzer] OpenCV 1fps 幀差分板書偵測 → Gemini OCR 轉 Markdown 關係圖
                   └→ [Merge Agent] Gemini 2.5 Pro 全文接縫精校 + 板書時戳嵌入
                        └→ [Formatter Agent] 
                             ├─ Step 1-8: 大綱提取、爭點標籤、標準字號/法條格式化
                             ├─ Step 9: 用 shutil.copy2 備份成果至 J:\ 原始目錄
                             └─ Step 10: 寫入 A:\processed_md\ 產出 5 大實體檔案
```

### 📦 轉錄成果落地規格 (SSOT)
每個任務完成後，以下檔案會同時保存在 `A:\processed_md\` 與 `J:\\` 影片原始目錄中：
1. `[課程名稱].md`：最終精校 Markdown 講義（包含逐字稿、階層大綱、核心爭點與板書筆記）。
2. `[課程名稱].srt`：標準繁體中文 SRT 字幕檔。
3. `[課程名稱].vtt`：標準 WebVTT 字幕檔。
4. `[課程名稱].txt`：純文字逐字稿（去時戳、去贅字）。
5. `[課程名稱]_index.json`：結構化段落索引（供 RAG 向量庫直接吸收）。

---

## 🛡️ 三、 系統可靠性與守護機制

針對本地雙 RTX 5060 Ti 顯卡與 49 把免費 Gemini API 金鑰池，系統內置了多重防護：

1. **配額管理器 (QuotaManager)**：
   * 位於 `scripts/quota_manager.py`，管理 49 把金鑰，日上限 980 次呼叫。
   * 自動識別 `429 RESOURCE_EXHAUSTED` 錯誤，抓取 API 回傳的精確秒數進行 cold down，並在單分片失敗 3 次後自動輪替下一把金鑰。
2. **硬體守護 (SystemGuard)**：
   * 監控 GPU 溫度（過 78°C 自動暫停，降溫後自動恢復）、VRAM 與 RAM。
   * 蒸餾引擎強制使用 **CPU-only int8** (`Whisper medium`)，防止 GPU 顯存溢出 (OOM) 與系統崩潰。
3. **工作流看門狗 (Watchdog Daemon)**：
   * 位於 `scripts/watchdog.py`，由 `Startup\LexMind-Watchdog.vbs` 綁定 Windows 使用者登入自動啟動。
   * 每 60 秒檢查一次：若工作流進程掛掉或日誌（`A:\logs\workflow.log`）停滯超過 10 分鐘，自動執行清鎖與安全重啟。

---

## ⚡ 四、 快速啟動與開發指南

### 1. 安裝依賴
```bash
# 安裝前端 Node 依賴
pnpm install
# 安裝 Python 依賴（必須包含 psutil, torch, faster-whisper, pyyaml 等）
pip install -r requirements.txt
```

### 2. 環境設定
確認根目錄下的 `.env` 或 `config.json` 設定正確。特別注意硬體紅線：
```ini
OLLAMA_HOST=http://127.0.0.1:11434  # Windows 11 必須用 127.0.0.1 避免 localhost IPv6 衝突
OLLAMA_GPU_ID=0                     # DeepSeek-R1:7b 鎖定 GPU-0
WHISPER_GPU_ID=1                    # Whisper / ChromaDB 鎖定 GPU-1
CHROMADB_GPU_ID=1
```

### 3. 一鍵啟動
*   **啟動 Web UI & API 服務**：
    ```bash
    npm run dev
    ```
*   **手動啟動工作流**（正常情況下由 Watchdog 自動管理）：
    ```bash
    python scripts/run_workflow.py
    ```
*   **啟動守護看門狗**：
    ```bash
    雙擊 "啟動守護程式.bat" 或重登 Windows 觸發啟動項目
    ```

---

## 📁 五、 核心檔案結構對照表

```
LexMind-Omni-法律實務-AI-工作站/
├── scripts/
│   ├── watchdog.py                 # 自動守護程式（每60秒健康檢查）
│   ├── run_workflow.py             # 佇列分發器與 SingleInstanceLock 實作
│   ├── preprocess_media.py         # FFmpeg 音訊降採樣
│   ├── chunk_planner.py            # 智慧靜音切片器
│   ├── stt_runner.py               # Gemini STT 聽寫與 DistillEngine
│   ├── merge_transcript.py         # Gemini 2.5 Pro 接縫精校
│   ├── markdown_formatter.py       # 大綱/爭點/標題/備份落地
│   └── quota_manager.py            # API 金鑰輪替與 cold down 策略
├── src/
│   ├── vector/
│   │   └── hybrid_search.py        # 混合檢索（Dense + BM25 + RRF）
│   └── legal_rag/
│       └── ingest_documents.py     # RAG 知識庫索引導入
├── config/
│   ├── quota_state.json            # 跨進程 API Key 狀態共享庫
│   └── config.yaml                 # 系統全域參數設定
└── 啟動守護程式.bat                  # Watchdog 啟動腳本
```