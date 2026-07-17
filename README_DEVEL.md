# ⚖️ 法律國考 AI 學霸助理與轉譯系統開發移交文件 (README_DEVEL.md - v5.0)

本文件專為 AI 帳號切換、專案重啟或新開發者接手時，快速銜接當前「法律國考 AI 學霸助理 (LexMind-Omni)」專案的最新開發狀態、系統架構以及下一步行動計畫所設計。

---

## 📂 一、 系統架構與自動化管線

系統採用 **「本地端重度 I/O + 雲端高階語意理解」** 的雙環分工設計：

```mermaid
graph TD
    subgraph 本地端 (Local Workstation)
        A[原始影音 MP4/隨身碟] -->|FFmpeg 降採樣| B(16kHz 單聲道 WAV)
        B -->|波形靜音偵測| C(12分鐘智慧斷句切片 Chunks)
        A -->|OpenCV 1fps 幀差分| D(穩定黑板板書快取圖片)
        E[(Qdrant & ChromaDB)] -->|本地混合檢索 BM25| F[LocalLegalAgent RAG]
    end
    
    subgraph 雲端 (Gemini API Cloud)
        C -->|Gemini 2.5 Flash| G(語音多模態聽寫 + 贅字同音錯字校正)
        D -->|Gemini 2.5 Flash| H(板書 OCR 手寫與關係圖結構化)
        G & H -->|Gemini 2.5 Pro| I(全文跨分片語意精校與拼接)
        I -->|Markdown Formatter| J(章節大綱/爭點加註/時戳板書融合成講義)
    end
    
    J -->|A:\\processed_md\\| K[(5 大落地實體檔案)]
    K -->|shutil.copy 自動備份| L[影片原始硬碟目錄 J:\\...]
```

詳細模組、Skills 與資料流介面規範請參考 **[README.md](file:///c:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/README.md)** 或全域架構報告 **[system_architecture_v5.md](file:///C:/Users/temp/.gemini/antigravity/brain/e59065cf-e4ec-4dfa-b18a-c0d1c3b095ba/system_architecture_v5.md)**。

---

## 📈 二、 目前開發進度與已修復項目

1. **多金鑰配額管理器 (QuotaManager)**：
   * 模組位於 `scripts/quota_manager.py`，管理 49 把金鑰（日上限約 980 次呼叫），跨進程共享 `config/quota_state.json` 狀態。當 API 遇到 429 RESOURCE_EXHAUSTED 限制時，會自動進行自適應睡眠冷卻，並在單分片失敗 3 次後輪替至下一組金鑰。
2. **工作流自動守護看門狗 (Watchdog)**：
   * 為了應對伺服器意外重啟或斷電，我們已部署了自動看門狗 `scripts/watchdog.py`，並在 Windows 開機啟動資料夾中建立了 VBS 捷徑：
     * 捷徑路徑：`C:\Users\temp\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\LexMind-Watchdog.vbs`
     * 作用：開機或使用者登入時自動啟動，每 60 秒檢查一次工作流進程與 `A:\logs\workflow.log` 日誌。若進程停止或日誌停滯超 10 分鐘，將自動清理鎖文件（`A:\manifests\workflow.lock`）並安全重啟工作流。
3. **Ollama IPv6 衝突修復**：
   * 修復了 `scripts/agent_core_pro.py` 中 Ollama 的連線問題（原為 `localhost:11434`，Windows 11 會優先解析為 IPv6 `::1` 造成連線被拒，現已統一修正為 `127.0.0.1:11434`）。
4. **DistillEngine 本地 OOM 防護**：
   * 本地蒸餾 Whisper 轉錄已被強制設定為 **CPU-only int8 (`Whisper medium`)**，不搶佔 GPU-1 的 ChromaDB/Gemini 備援資源，防止本地 VRAM/RAM 溢出造成系統崩潰。
5. **吸收管線 (Ingestion Pipeline) 防呆與防幻覺機制升級 (v5.1)**：
   * 實裝了 `0.6 ~ 1.5 KB/min` 的講義密度雙向防護網，精準攔截 Whisper 無限迴圈產生的幻覺垃圾檔案。
   * 全面實裝了 `is_file_content_legal` 國考白/黑名單過濾機制於背景管線入口 `file_watcher.py`，強制封殺「法規庫、空大、房仲、私人協調錄音」等非國考教材。
   * 修復了 `auto_ingest_bot.py` 與 `file_watcher.py` 中因路徑解析邏輯錯誤導致合法課程被強制降級為「預設課程」的 Bug。現在來自 H 碟與 J 碟的課程已能正確繼承父資料夾名稱（如 `[行政法霖迴B115_ch27]`）。

---

## ⚖️ 三、 30 堂大型法律教材：終極驗收標準 (Acceptance Criteria)

必須**自動批次完成 30 份真實課程，全程無當機、無錯誤**。驗收指標如下：

### 1. 檔案落地與雙目錄備份（核心物理交付物）
每個任務必須成功產生 5 個帶有課程前綴名稱的實體檔案，且同時存在於 `A:\processed_md\` 與影片原始存放目錄（如 `J:\土地登記\ch1\`）：
- [ ] `[課程名稱].md`：最終精校 Markdown 講義（包含逐字稿、階層大綱、核心爭點與板書筆記）。
- [ ] `[課程名稱].srt`：標準繁體中文 SRT 字幕檔。
- [ ] `[課程名稱].vtt`：標準 WebVTT 字幕檔。
- [ ] `[課程名稱].txt`：純文字逐字稿（去時戳、去贅字）。
- [ ] `[課程名稱]_index.json`：RAG 向量庫檢索結構化 JSON 索引。

### 2. 臺灣法律專業品質（正確率 ≥ 98%）
- [ ] **贅字過濾**：100% 過濾「那個、然後、就是說、呃、啊」等口口頭贅詞，保持句型流暢。
- [ ] **消滅同音錯字**：臺灣法律專業術語精準辨識，不得有同音字誤識。
  * *錯誤範例*：投地登記、地政治、消滅實效、共耳、優購權。
  * *正確範例*：土地登記、地政士、消滅時效、共有人、優先購買權。
- [ ] **格式標準化**：統一法條格式（如「民法第197條」）與字號格式（如「釋字第474號解釋」）。

---

## 🚧 四、 當前狀態與下一步行動

### 1. 佇列消化狀態
*   **佇列總數**：265 堂課
*   **目前完成進度**：2/265
*   **狀態**：背景 Daemon 進程與 Watchdog 正在穩定執行中，逐步消化佇列。
*   **累積蒸餾數據**：3 / 5,000 條對照數據（累積達 5,000 條後，可進行本地 14B QLoRA 模型微調）。

### 2. 接手開發者/Agent 下一步行動指引
1.  **監控佇列消化**：
    *   定期使用 `Get-Content A:\logs\workflow.log -Tail 20` 檢查轉錄管線進度。
    *   使用 `Get-Content A:\logs\watchdog.log -Tail 10` 監控守護程式是否正常執行。
2.  **品質抽樣驗證**：
    *   隨時抽樣 `A:\processed_md\` 新落地的 Markdown 講義檔案，檢查同音字修正率與贅字過濾情況，以確保品質達到 98% 台灣法律實務標準。
3.  **微調資料累積**：
    *   持續監視 `A:\distillation_data\legal_distillation_pairs.jsonl`，等待累積達 5,000 條後啟動 Phase 5 Unsloth 訓練。

---

## 🚀 五、 專案演進與本地化藍圖 (Strategic Roadmap)

未來的演進方向將朝向「完全自主」與「零 API 費用」的本地化部署，擺脫對雲端大模型的依賴，並藉由蒸餾（Distillation）將法律理解能力轉移至本地開源模型。

```text
現在                    2~3週後                  1個月後              3個月後
 │                        │                        │                    │
 ▼                        ▼                        ▼                    ▼
[資料採集]           [QLoRA 微調]            [本地部署]          [完全自主]
265 堂課跑完  →  5,000~10,000 條訓練對  →  Qwen2.5-14B    →  脫離 Gemini
Whisper+Gemini     Unsloth 雙卡訓練        法律精校小天才      零 API 費用
自動採集 CoT       ~16小時完成訓練         Ollama 本地推理     98%+ 精確率
```

| 日期 | 並發數 | MAX_RPM | 有效 key 數 | 實測 KPI |
|---|---|---|---|---|
| 2026-07-13 | 6 | - | - | 防止 16:00 STT Phase B 觸發 GPU 逾時藍白當機 (0x00000133) 下修上限 |
