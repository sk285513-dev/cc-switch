# ⚖️ LexMind-Omni 法律教材工作站除錯與架構優化技術報告

## 📌 1. 背景與任務目標
本專案旨在處理超過上千堂、單堂時長達 2.6 小時的繁體中文法律影音教材。目標是在使用**免費雲端 API（Gemini 72B+ 級別）**的前提下，產出正確率高達 98%+ 的臺灣繁體中文逐字稿、字幕與索引文件，並完全排除口語贅字與同音錯字（如將「各論」寫成「格論」）。

---

## 🛠️ 2. 核心除錯與架構優化歷程

### 🔴 痛點一：本機 CPU/GPU 超載與記憶體崩潰
*   **問題描述**：舊版系統在啟動時，會同時並行處理音訊轉檔、分片與 GPU 轉寫。在面對 2.6 小時的超級大檔時，多任務並行導致 CPU 暴衝至 100%、系統實體記憶體（RAM）與顯存（VRAM）瞬間溢出，引發工作站當機。
*   **優化方案**：
    1.  **「白天 CPU 離線分片，下午 API 限額精校」**：開發並部署了 `--chunking-only` 離線模式。白天僅使用 CPU 進行低負載的音軌提取與 12 分鐘靜音精準切片，不佔用任何 GPU/VRAM。
    2.  **動態併發防護**：建立了動態併發與緊急暫停機制，定時監測顯卡溫度（>78°C 降載，>80°C 暫停）與 RAM 佔用，保護雙 RTX 5060 Ti 顯卡。

### 🔴 痛點二：雲端 API 單日 429 額度超限 (RESOURCE_EXHAUSTED)
*   **問題描述**：Gemini API 免費金鑰受限於每日配額。一堂 2.6 小時的課程切成 ~13 個分片，需消耗大量呼叫次數，導致金鑰快速被限制，管線中斷。
*   **優化方案**：
    1.  **49 把金鑰輪替池**：在 `quota_manager.py` 中建立金鑰狀態共享機制。當連線出現 429 錯誤時，系統自動提取 API 回傳的精確秒數進行 cold down，並在單分片失敗 3 次後自動輪替至下一組金鑰。
    2.  **跨進程狀態庫**：使用 `quota_state.json` 全局共享狀態，使 STT、精校與板書 OCR 模組協同，避免多進程衝突。
    3.  **日配額量**：49 把金鑰池提供每日約 980 次的呼叫容量，可供消化上百堂課程。

### 🔴 痛點三：本機 Whisper 語音轉寫 (STT) 的法律精確度不足
*   **問題描述**：本機小參數模型對台灣法律專用術語辨識度不佳，且容易與同音錯字混淆（如「地政士」聽成「地政治」）。
*   **優化方案**：
    1.  **雙軌蒸餾採樣**：確立 100% 使用雲端 Gemini API（Flash + Pro 級別）進行聽寫與語意精校，同時於背景線程以 **CPU-only int8 (`Whisper medium`)** 進行本地對照轉寫，收集並累積 `{Whisper稿 -> Gemini精校稿}` 蒸餾對話數據。
    2.  **微調目標**：累積達 5,000 條後，即可執行本地 14B 模型的 QLoRA 特化微調，最終實現零 API 成本的純本地端精準轉譯。

### 🔴 痛點四：Windows 終端機 Unicode 輸出崩潰
*   **問題描述**：輸出簡體或特殊 Unicode 字元時，在 Windows 預設 `cp950`（Big5）編碼終端下 print 會拋出 `UnicodeEncodeError` 導致腳本崩潰。
*   **優化方案**：在各腳本入口強制設定 `sys.stdout.reconfigure(encoding='utf-8')`。

### 🔴 痛點五：伺服器意外重啟與進程停滯 (NEW 2026-07-09)
*   **問題描述**：工作站斷電、Windows 自動更新或重啟會中斷正在跑的 Python 背景佇列進程，且 API 長期睡眠等待時容易陷入假死。
*   **優化方案**：
    1.  **自動守護看門狗 (Watchdog)**：部署 `watchdog.py`，設定為 Windows 開機自動啟動。
    2.  **健康檢查**：每 60 秒檢查一次，若偵測到 `run_workflow.py` 消失或日誌停滯 > 10 分鐘，自動執行清鎖並安全重啟。

### 🔴 痛點六：Ollama localhost IPv6 衝突 (NEW 2026-07-09)
*   **問題描述**：在 Windows 11 下 `localhost` 優先被解析為 IPv6 `::1`，而 Ollama 本地端僅監聽 IPv4 端口，導致 LocalLegalAgent 呼叫 LLM 失敗或超時。
*   **優化方案**：將 `agent_core_pro.py` 中所有的連線網址從 `localhost` 強制改為 `127.0.0.1` 避開解析衝突。

---

## 📂 3. 部署架構與關鍵檔案清單

1.  **[README.md](file:///c:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/README.md)**：全域真理源，記錄系統七層架構、管線運作與快速啟動指引。
2.  **[scripts/watchdog.py](file:///c:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/scripts/watchdog.py)**：守護看門狗，保證 265 堂佇列在背景不間斷消化。
3.  **[scripts/run_workflow.py](file:///c:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/scripts/run_workflow.py)**：任務佇列分發，支援 SingleInstanceLock 與 mock 任務優先插隊。
4.  **[scripts/stt_runner.py](file:///c:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/scripts/stt_runner.py)**：分片轉寫與本地 Whisper 蒸餾數據採集。
5.  **[scripts/quota_manager.py](file:///c:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/scripts/quota_manager.py)**：接管所有 API Key 退避與輪替。
6.  **[scripts/agent_core_pro.py](file:///c:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/scripts/agent_core_pro.py)**：LocalLegalAgent 主邏輯，使用雙重單例保護 ChromaDB 連結，防止 DB 鎖死。

---

## 📈 4. 自動化 Agent 協同架構
*   **`dispatch_coordinator` (自動派工 Agent)**：根據金鑰池 Active Key 數量，啟動並發 Worker 消化 `A:\manifests\` 中的 task JSON。
*   **`cloud_quota_supervisor` (資源與配額監督 Agent)**：隨時檢查硬體狀況（GPU溫度、VRAM），預估 API 限額。
*   **`SystemGuard MCP`**：提供 `system-guard-watchdog` 實時熔斷降級機制。
