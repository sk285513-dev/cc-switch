# ⚖️ 法律國考 AI 學霸助理與轉譯系統開發移交文件 (README_DEVEL.md - v5.0)

本文件專為 AI 帳號切換、專案重啟或新開發者接手時，快速銜接當前「法律國考 AI 學霸助理 (LexMind-Omni)」專案的最新開發狀態、系統架構以及下一步行動計畫所設計。

---

## 一、 系統架構與自動化管線

系統採用 **「本地端重度 I/O + 雲端高階語意理解」** 的雙環分工設計：

`mermaid
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
    
    J -->|A:\processed_md\| K[(5 大落地實體檔案)]
    K -->|shutil.copy 自動備份| L[影片原始硬碟目錄 J:\...]
`

詳細模組、Skills 與資料流介面規範請參考 **[README.md](file:///c:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/README.md)** 或全域架構報告 **[system_architecture_v5.md](file:///C:/Users/temp/.gemini/antigravity/brain/e59065cf-e4ec-4dfa-b18a-c0d1c3b095ba/system_architecture_v5.md)**。

---

## 二、 當前狀態與專案演進藍圖 (Strategic Roadmap)

未來的演進方向將朝向「完全自主」與「零 API 費用」的本地化部署，擺脫對雲端大模型的依賴，並藉由蒸餾（Distillation）將法律理解能力轉移至本地開源模型。

`	ext
現在                    2~3週後                  1個月後              3個月後
 │                        │                        │                    │
 ▼                        ▼                        ▼                    ▼
[資料採集]           [QLoRA 微調]            [本地部署]          [完全自主]
265 堂課跑完  →  5,000~10,000 條訓練對  →  Qwen2.5-14B    →  脫離 Gemini
Whisper+Gemini     Unsloth 雙卡訓練        法律精校小天才      零 API 費用
自動採集 CoT       ~16小時完成訓練         Ollama 本地推理     98%+ 精確率
`

| 日期 | 並發數 | MAX_RPM | 有效 key 數 | 實測 KPI |
|---|---|---|---|---|
| 2026-07-13 | 6 | - | - | 防止 16:00 STT Phase B 觸發 GPU 逾時藍白當機 (0x00000133) 下修上限 |

---

## 三、 當前開發進度 (v6.0 部署與已知問題)

- **V6 藍綠部署**：系統目前正處於 V6 沙盒驗證階段，啟動檔為 C:\LocalAI_Workstation\LexMind_V6_沙盒驗證版.ps1，核心腳本位於 scripts_v6/。
- **WinError 10106 問題**：當前 V6 的背景服務啟動腳本使用了 pythonw 且未導向輸出，導致 chromadb (asyncio) 啟動時發生 10106 I/O 錯誤。
- **解決方案**：須將啟動腳本與監控腳本中的 pythonw 修改為 python，並配合 -RedirectStandardOutput 與 -RedirectStandardError 將日誌導出至實體檔案。

---

## 四、 AI 溝通與文件交付最高指導原則 (Supreme Communication Rules)

**本條為使用者今日（2026-08-02）親自下達之最重要鐵律，任何接手之 AI 皆須無條件遵守，絕不可在系統重置或交接時遺失：**

0. **角色限制與專業分工 (Role Restriction & Delegation)**：
   * **非 Sonnet 模型 (如 Gemini) 絕對禁止主動修改或設計程式碼**。Gemini 的角色被嚴格限定為「文件整理、環境盤點與驗收檢查」的專業發包商。任何實際的程式碼撰寫與修改，必須保留給 Sonnet 等專門的 Coder 模型執行，Gemini 只能進行分析與任務交付，絕不准越俎代庖。
1. **未經允許，禁止刪改 (No Unauthorized Modifications)**：
   * **絕不准亂刪東西未經使用者允許，也不准寫東西未經使用者允許！** 這是最高原則。任何直接「自作主張」覆蓋或刪減使用者心血的行為，視同嚴重破壞。
2. **先展示，後動作 (Show Before Action)**：
   * 在對現有文件（如 AGENTS.md、README_DEVEL.md 或任何腳本）進行大範圍刪減或重構時，**必須先把準備刪除或修改的片段「框起來（使用 Markdown Code Block 或 Diff 格式）」展示給使用者看**。
   * 向使用者說明這段是否為廢話、是否要修改或刪除，**等待使用者確認並下達「同意刪除」或「同意修改」的指令後**，才能真正動手修改。
3. **除錯交接素材準備工作習慣 (Diagnostic Handoff Protocol)**：
   * 當需要移交錯誤日誌與原始碼給另一個 AI 除錯時，必須遵守以下標準：
   * **單一純文字檔合併**：將需要除錯的「完整程式碼」與「錯誤日誌」合併至單一 .txt 檔案中。
   * **直接落地實體工作區**：檔案必須直接自動存入 C:\LocalAI_Workstation\，讓使用者直接能在本機看得到。
   * **嚴禁檔名加時間戳記**：**絕對禁止**在檔案名稱上加入任何時間或版本後綴（例如禁止使用 workflow_debug_20260802.txt）。保持檔名乾淨，最新版本直接依賴 Windows 檔案總管的「修改時間」即可。
   * **禁止洗版**：**嚴禁只在對話框輸出大段程式碼（上限 50 行）。**

---

## 五、 多代理人獵頭招募與程式碼審查鐵律 (Agentic Headhunter & Review Protocol)

為了達成將 72B 雲端模型蒸餾至本地 16GB (7B) 模型的終極願景，所有接手開發的子代理人 (Subagents) 皆須被視為「具備資訊工程與法律 AI 雙專業」的雙棲專家。發包與審核必須遵守以下鐵律：

### 1. 程式碼審核 8 大鐵律 (Windows & 系統環境防崩潰)
1. **禁止終端機輸出 Emoji**：Windows 預設 CP950 無法解析 Emoji。print() 或 Write-Host 中包含 Emoji 將導致 UnicodeEncodeError 並使進程卡死。
2. **純 ASCII 圖示安全化**：終端機提示僅限使用純 ASCII 符號（如 [OK], [WARN], [FAIL]），嚴禁為了美觀添加任何特殊字元。
3. **強制腳本編碼**：所有寫入的 Python (.py) 與 PowerShell (.ps1) 檔案，必須強制使用 UTF-8 或 UTF-8-BOM 編碼。
4. **CP950 日誌讀取防護**：讀取 Windows 日誌遇到中文字節 (0xa6) 易噴錯，讀檔時務必加上  rrors="replace" 或  rrors="ignore"。
5. **字典取值 KeyError 防呆**：嚴禁硬抓 JSON 欄位（如 manifest["task_id"]）。必須強制使用安全的 .get() 方法（如 manifest.get("task_id", "unknown")）。
6. **API 呼叫無聲死鎖防禦**：呼叫 Vertex AI / Gemini 等外部 API 時，絕對不可漏設 	imeout（如 	imeout=120.0），避免 Worker 永久掛起。
7. > [!CAUTION]
> # 🛑 絕對禁止觸碰的底層禁忌 (V6.1 黃金獨立版)
> 1. **啟動器架構已定死 (嚴禁使用 pythonw 隱藏視窗)**：目前全系統的一鍵啟動腳本必須比照 V4、V5 時代，維持使用**原版、獨立的 `python.exe` 配合 `Start-Process powershell` 彈出獨立監控視窗**！這是唯一能解決 WinError 10106 Pipe 死鎖的解法。**任何接手 AI 絕對禁止自作聰明發明 `Launch_Isolated.py` 或改用 `pythonw.exe` 試圖把視窗藏到背景！**
> 2. **BOM 編碼禁區**：所有 `.py` 與 `.ps1` 都已由 Git Pre-commit Hook 強制鎖定 UTF-8 BOM。**不准用任何會剝除 BOM 的文字寫入工具去改寫檔案。**
8. **KPI 監視器假死盲點**：進程存活不代表運作正常。KPI 邏輯強制規定：「連續 3 輪 (15分鐘) Chunk 產出為 0，即視為故障並強制重啟」。

### 2. 已修復與待防護的 4 大底層架構地雷
9. **金鑰輪替的 Race Condition (stt_runner.py)**：發生 429 錯誤時，嚴禁抓取全域最新金鑰來記錯（會誤殺剛換上的新金鑰）。必須強迫使用當下發出請求的局部變數  ctive_key。
10. **例外退避機制的 5 大死角 (stt_runner.py)**：遇到 API 429/503/Timeout 時，必須確保：(a) 累加 etry_count 防止無窮迴圈。(b) 加上 Sleep 緩衝防連發。(c) 任務徹底死亡時必須推播 ailed 狀態給 UI 避免幽靈進度。
11. **Windows 重啟腳本的獨佔鎖地雷 (restart_workflow.ps1)**：un_workflow.py 與 watchdog.py 嚴禁共用同一個 Log 檔（會觸發 Sharing Violation）。寫入 JSON 時須採用無 BOM 寫法，避免污染資料庫。
12. **Traceback 切割與日誌斷行 (sre_watchdog.py)**：逐行讀取日誌會把 Python 例外 (Traceback) 砍斷導致正則匹配失效。必須加入 Buffer 機制，確保完整的 Exception Block 被合併後再發送。

### 3. 發包商無情淘汰制 (Fire or Hire)
13. **零幻覺要求**：代理人產出的程式碼若缺乏錯誤處理、帶有幻覺或不符合法律嚴謹度，將直接退件 (Fire)；僅有產出穩定、高併發且狀態追蹤精準的邏輯，才會被採納。

