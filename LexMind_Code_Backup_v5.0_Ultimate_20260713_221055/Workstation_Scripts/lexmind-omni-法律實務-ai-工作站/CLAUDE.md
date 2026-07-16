# LexMind-Omni CLAUDE.md 代理防禦協議 (Local Agent Protocol)

## 🚪 軟體工程與除錯紀律

* **視窗代碼輸出禁令 (絕對禁止視窗罰抄)**：嚴禁在聊天對話中輸出超過 50 行的代碼，以防範 KV Cache 爆炸。所有代碼變更必須直接靜默調用原生檔案編輯工具處理。
* **除錯回滾協議**：若連續 3 輪除錯 Bug 未減或發生錯誤漂移，必須執行 git checkout 或 Rollback 退回安全的綠色節點，重新審視底層邏輯。
* **記憶體與顯存管理**：在 Ingestion 與 chat 循環中，必須加入明確的 gc.collect() 與 torch.cuda.empty_cache()，以防止 OOM。

## ⚙️ 48GB DRAM 硬體配置與平行分流防線

* **CPU 執行緒限制**：
  - 全局限制 OMP_NUM_THREADS = 4 與 MKL_NUM_THREADS = 4。
* **GPU 任務平行分流**：
  - **GPU-0**：專職執行 Ollama 本地推理任務。
  - **GPU-1**：專職執行 ChromaDB 向量檢索、ONNX 與 Whisper 語音轉錄。
* **ChromaDB 單例防護 (Singleton)**：
  - ChromaDB 連線必須採用單例模式保存，嚴禁在對話或循環中重複初始化 PersistentClient()。

## ⚖️ 台灣法律開發規範

* 答覆中絕對禁止出現「公安、檢察院、被告人」等大陸法律用語，必須使用三段論法與正統繁體中文（如「警察/司法警察、檢察官、被告」）。
* 對話內容與分析需符合中華民國法律規範。
