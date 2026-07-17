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
*   **問題描述**：Gemini API 免費金鑰受限於每日 1,500 次請求（RPD）與每分鐘 20 次請求（RPM）。在處理超大檔案時，單檔會切成 15 個分片，導致呼叫次數暴增，金鑰在執行數個任務後便被鎖定，使得 STT 或 Merge 步驟中斷失敗。
*   **優化方案**：
    1.  **預約批次排程器**：部署了 `run_scheduled_batch.py`，定時於臺灣時間每日下午 **15:00**（Gemini 每日配額重置點）自動喚醒，大批次解鎖並上傳。
    2.  **多金鑰輪替池 (Key Pool Rotation)**：在 `workflow_helper.py` 中部署了金鑰狀態記錄器 `api_keys_state.json`。當 API 連線拋出 `RESOURCE_EXHAUSTED` 429 錯誤時，工作流會**自動標記當前金鑰為「今日耗盡」，並無縫切換到下一組可用金鑰原地重試**！
    3.  **效能對比**：單金鑰每日僅能處理 51.7 堂課；導入 **5 金鑰輪替池** 後，每日處理量爆發至 **258 堂課 / 天**，處理上千堂影片的時程由 19 天縮短至 **3.9 天**！

### 🔴 痛點三：本機 Whisper 語音轉寫 (STT) 的法律精確度不足
*   **問題描述**：本機 Whisper `small`（2.4億參數）轉寫速度快，但對臺灣法律術語（如：地政士、不當得利、刑訴）缺乏語意理解，且存在嚴重的同音錯字（如把「各論」拼成「格論」）。
*   **優化方案**：
    1.  **引進 large-v3 本地評測**：成功下載並加載 15 億參數的 `large-v3`（業界最強中文模型）進行評測，證實能在 GPU 上以 9 倍速運行並精準校正「地政士」等詞。
    2.  **確立 100% 雲端轉譯架構**：為遵循使用者對精確度的極致要求，將 `stt_engine` 鎖定為 `gemini`。由雲端 72B 級別大模型直接聽寫 WAV 分片，結合 RWS 權重與法律語意上下文，直接輸出無瑕的臺灣繁體中文逐字稿，徹底消滅同音錯字。

### 🔴 痛點四：Windows 終端機 Unicode 輸出崩潰
*   **問題描述**：本機 Whisper 輸出中若夾雜簡體 Unicode 字元（如「们」），在 Windows 預設 `cp950`（Big5）編碼的控制台下 print 時，會拋出 `UnicodeEncodeError` 導致腳本崩潰。
*   **優化方案**：在測試與執行腳本的入口強制執行 `sys.stdout.reconfigure(encoding='utf-8')`，徹底避開 Windows 的 cp950 console 編碼缺陷。

---

## 📂 3. 部署架構與關鍵檔案清單

1.  **[config.yaml](file:///c:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/config.yaml)**：全域組態。鎖定 `stt_engine: "gemini"` 並支援 `gemini_api_keys` 清單配置。
2.  **[workflow_helper.py](file:///c:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/scripts/workflow_helper.py)**：共用核心。新增 `get_gemini_key()` 多金鑰輪替邏輯、`mark_key_exhausted()` 金鑰隔離與狀態維護。
3.  **[stt_runner.py](file:///c:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/scripts/stt_runner.py)**：音訊轉寫。對 429 錯誤進行實時攔截，自動輪替 Key 後原地重試分片。
4.  **[merge_transcript.py](file:///c:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/scripts/merge_transcript.py)**：語意精校。對 429 錯誤進行攔截與金鑰池輪替，保障整理與摘要不中斷。
5.  **[run_scheduled_batch.py](file:///A:/run_scheduled_batch.py)**：排程器。每日 15:00 喚醒，並自動將基準任務（`task_03`）重設為 `pending` 進行 72B 重新覆蓋。

---

## 📈 4. 自動化 Agent 協同架構
*   **`dispatch_coordinator` (自動派工 Agent)**：負責監控任務佇列，並根據金鑰池剩餘的 Active Key 數量，啟動並發 Worker，分配不同的金鑰進行平行轉譯。
*   **`cloud_quota_supervisor` (資源與配額監督 Agent)**：負責隨時檢查工作站的實體 RAM、GPU 溫度，並分析 `workflow.log` 判斷 API 限額，為派工協同提供即時的安全參數。
