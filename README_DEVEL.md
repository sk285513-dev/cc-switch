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

---

## 💻 六、 當前開發進度 (v6.0 部署與已知問題)
- **V6 藍綠部署與啟動腳本唯一性宣告**：系統唯一的正式啟動腳本為 `C:\LocalAI_Workstation\LexMind_一鍵正式啟動.ps1`。已於 2026-08-05 將沙盒驗證版的 WMI 防護機制與遺漏的 Dashboard 視窗修補至正式版。嚴禁未來任何 AI 讀取、執行或修改 `LexMind_V6_沙盒驗證版.ps1` 或其他帶有沙盒字眼的測試腳本。
- **WinError 10106 問題**：當前 V6 的背景服務啟動腳本使用了 pythonw 且未導向輸出，導致 chromadb (asyncio) 啟動時發生 10106 I/O 錯誤。
- **解決方案**：須將啟動腳本與監控腳本中的 pythonw 修改為 python，並配合 -RedirectStandardOutput / -RedirectStandardError 將日誌導出至實體檔案。

---

## 🤝 七、 AI 溝通與文件交付最高指導原則 (Supreme Communication Rules)
**本條為使用者今日（2026-08-02）親自下達之最重要鐵律，任何接手之 AI 皆須無條件遵守，絕不可在系統重置或交接時遺失：**

1. **未經允許，禁止刪改 (No Unauthorized Modifications)**：
   * **絕不准亂刪東西未經使用者允許，也不准寫東西未經使用者允許！** 這是最高原則。任何直接「自作主張」覆蓋或刪減使用者心血的行為，視同嚴重破壞。
2. **先展示，後動作 (Show Before Action)**：
   * 在對現有文件（如 AGENTS.md、README_DEVEL.md 或任何腳本）進行大範圍刪減或重構時，**必須先把準備刪除或修改的片段「框起來（使用 Markdown Code Block 或 Diff 格式）」展示給使用者看**。
   * 向使用者說明「這段是否為廢話、是否要修改或刪除」，**等待使用者確認並下達「同意刪除」或「同意修改」的指令後**，才能使用工具進行實際的檔案寫入。
3. **除錯交接素材準備工作習慣 (Diagnostic Handoff Protocol)**：
   * 當需要移交錯誤日誌與原始碼給另一個 AI 除錯時，必須遵守以下標準：
   * **單一檔案合併**：將需要除錯的「完整程式碼」與「錯誤日誌」合併至單一 Markdown (.md) 檔案中。
   * **寫入 UI Artifacts**：必須使用檔案寫入工具將該 Markdown 寫入 UI Artifact 資料夾中，供使用者下載。**嚴禁只在對話框輸出大段程式碼（上限 50 行）。**
   * **檔名押上精確時間**：除錯交接檔案的命名必須包含精確時間戳記（例如 workflow_debug_20260802_1158.md）。
   * **同步落地實體工作區**：必須同時將同一份內容直接寫入 C:\LocalAI_Workstation\，不可僅依賴 UI 下載。
4. **絕對程式碼修改邊界 (Absolute Code Modification Boundary)**：
   * **你絕對不准寫程式或修改現有程式碼，唯一的例外只有「三支你的專屬工具」**：
     1. 一鍵正式啟動腳本 (`LexMind_一鍵正式啟動.ps1`)
     2. 一鍵完全關閉腳本 (`LexMind_一鍵完全關閉系統.ps1`)
     3. 自動除錯與監控工具 (`auto_telemetry_debugger.py` / `auto_vision_debugger.py`)
   * 這三支程式是「你的測試與操作工具」，你可以在使用環境底下「任意修改與優化」它們，直到它們能完美運作為止。
   * **但是，對於這三支工具以外的所有主程式與 11 支腳本，你「絕對不准動任何修改的念頭」！** 針對主程式，你只能透過你的工具去測試，並寫出「發現問題的報告與計畫」，等待使用者的最終裁決。
5. **【架構鐵律：app_v6.py 與 11 支核心腳本的共生關係】**：
   * `app_v6.py` 是唯一的官方 UI，它與背景的 11 支腳本（如 `run_workflow.py`）是緊密連動的共生體。背景腳本負責做事並將狀態寫入 `.json`，由 `app_v6.py` 讀取並顯示。 過去有 AI 誤將 `app_v6.py` 稱為「幽靈腳本」或「空殼」，甚至企圖切斷 11 支腳本與它的聯繫，這是極度荒謬且嚴格禁止的破壞行為！任何接手的 AI 絕對不准清理、刪除這 11 支腳本或 `app_v6.py`。 真正的幽靈是過去 AI 亂寫的 `patch_` 系列補丁。未來的除錯只能專注於修復這 11 支腳本在啟動時遇到的 I/O 閃退問題，讓它們重新順利交談！

## 🛡️ 八、 外部除錯程式碼之核准與覆寫標準 (V6 防禦交接)
**【接手 AI 必讀：當使用者帶回外部 Coder 寫好的修復程式碼時，必須嚴格執行以下審查，合格後才可貼回，不合格直接打退票！】**

1. **精確對位覆寫 (Target Verification)**：
   - 接到新的程式碼後，**必須清楚知道這要貼回去哪裡**（例如明確指向 C:\LocalAI_Workstation\scripts_v6\run_workflow.py）。
   - 絕對不要在沒有確認目標檔案的情況下亂貼，或者擅自建立過渡檔案。

2. **13 大鐵律逐一安檢 (Ironclad Rules Check)**：
   - 貼回前，必須用本專案的「13 大鐵律」逐一檢查（例如：是否偷用了 ensure_ascii=False？是否忘了 errors="replace"？是否缺少 timeout？）。
   - 只要有一條不合格，**立刻打退票 (Reject)**，要求使用者退回給 Coder 重寫。

3. **幽靈檔案與幽靈指標防護 (Anti-Ghosting Scan)**：
   - 必須特別檢查早上發生的「幽靈檔案」問題！
   - 檢查新程式碼中的 import、檔案路徑或呼叫函數：如果新腳本中出現了指向「不存在的幽靈腳本名稱」或是「不存在的路徑」，代表外包 Coder 又發作了幻覺。
   - **一旦發現幽靈指向，必須立刻打退票！** 絕對不要抱著僥倖心態照貼，然後在那邊傻傻地亂測引發災難。

---

## 🛠️ 九、 官方診斷與測試腳本庫 (Diagnostic & Testing Toolkit)
**【接手 AI 必讀：嚴禁角色扮演或憑空瞎掰測試結果！所有 V6 除錯與測試，必須無條件優先使用以下前人留下的官方腳本，禁止重新造輪子！】**

當需要驗證系統狀態、修復 Bug 或是進行單元測試時，請務必直接呼叫以下位於 `scripts_v6/` 或根目錄的專用腳本：

### 1. 核心通道與防撞測試 (通道暢通度驗證)
- **`C:\LocalAI_Workstation\test_vertex_adc.py`**：獨立測試 Vertex AI 企業通道與 ADC 憑證是否順暢。**當遇到 LLM 回應超時或憑證報錯時，第一時間跑這個。**
- **`scripts_v6/test_duplicate.py`**：壓力測試腳本，用來模擬並驗證 `inflight_guard` (防撞車鎖) 機制是否正常運作。

### 2. 系統清理與健康檢查 (殭屍任務與殘檔清理)
- **`scripts_v6/verify_workflow_health.py`**：工作流健康檢查器，掃描並列出是否有卡死的殭屍任務。
- **`scripts_v6/clean_half_processed.py` / `clean_half_processed_safe.py`**：安全清理卡在一半、殘缺不全的半成品暫存檔，釋放系統卡死的狀態。

### 3. I/O 錯誤與模組熱修復補丁 (緊急外科手術)
遇到 `pythonw` 導致的 `10106 I/O Error` 或特定模組崩潰時，優先執行現有修補補丁：
- **`scripts_v6/patch_fix3_surgical.py`**：外科手術式修補腳本（專門精準修改 `run_workflow.py` 的標準輸出）。
- **`scripts_v6/patch_fix2b_reconfigure_safe.py`**：安全設定標準輸出的腳本（強制寫入 UTF-8 以避免報錯）。
- **`scripts_v6/patch_markdown.py` / `restore_markdown.py`**：針對 `markdown_formatter.py` 進行熱修復與備份還原。

**💡 驗收官自我警惕：**
若使用者要求測試，請直接以 `python [腳本名稱]` 執行上述對應工具，並將真實的終端機輸出回報給使用者。絕對不准用「我已經幫您在腦海中跑過了」等敷衍話術！

### 4. 歷史測試指令與環境配置標準 (Testing Methodologies)
前人 AI 留下來的除錯經驗與指令下達標準，所有後續測試皆須依循此配置：

- **啟動背景測試的最佳實踐 (取代會當機的 pythonw)**：
  使用 PowerShell 的 `Start-Process` 並強制重新導向 I/O，以防 `10106` 崩潰：
  ```powershell
  Start-Process python -ArgumentList "scripts_v6\run_workflow.py" -RedirectStandardOutput A:\logs_v6\run_workflow_stdout.log -RedirectStandardError A:\logs_v6\run_workflow_stderr.log -WindowStyle Hidden
  ```
- **測試前的環境變數注入**：
  在進行任何單元測試或指令碼執行前，必須先在 PowerShell 終端機宣告以下環境變數，以確保編碼與路徑正確：
  ```powershell
  $env:LEXMIND_ENV="v6_canary"
  $env:PYTHONUTF8="1"
  $env:PYTHONIOENCODING="utf-8"
  $env:LEXMIND_WORKDIR="C:\LocalAI_Workstation"
  ```
- **清空殭屍進程 (Nuclear Option)**：
  在重新測試前，務必先砍乾淨所有殘留的 Python 進程，避免 Port 佔用或鎖死：
  ```powershell
  taskkill /F /IM python.exe /T 2>&1 | Out-Null
  taskkill /F /IM pythonw.exe /T 2>&1 | Out-Null
  ```
- **即時監控日誌**：
  測試啟動後，不應瞎猜，必須即時監聽日誌輸出：
  ```powershell
  Get-Content A:\logs_v6\workflow.log -Tail 30 -Wait -Encoding UTF8
  ```

### 5. 專家進階除錯技巧 (Advanced Debugging Techniques)
來自 Perplexity / Anthropic 專家的除錯精華，用於深度排錯與狀態重置：

- **驗證程式碼完整性 (SHA256)**：
  在除錯前，使用雜湊值確認檔案是否被其他 AI 偷偷竄改：
  ```powershell
  Get-FileHash scripts_v6\*.py -Algorithm SHA256
  ```
- **強制修復 UTF-8 BOM 編碼 (防禦 CP950 崩潰)**：
  若 Python 檔案缺少 BOM 導致編碼炸彈，可用此 PowerShell 腳本強制補齊：
  ```powershell
  cd C:\LocalAI_Workstation\scripts_v6
  foreach ($f in "run_workflow.py","stt_runner.py") {
      $b = [System.IO.File]::ReadAllBytes("$PWD\$f")
      if (-not ($b.Length -ge 3 -and $b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF)) {
          [System.IO.File]::WriteAllBytes("$PWD\$f", [byte[]](0xEF,0xBB,0xBF) + $b)
      }
  }
  ```
- **手動重置任務狀態 (Replay Task)**：
  為了重複測試特定工作流階段，可以直接用 PowerShell 修改 Manifest JSON 狀態：
  ```powershell
  $id = "task_xxx"
  $m = Get-Content "A:\manifests_v6\$id.json" -Raw -Encoding UTF8 | ConvertFrom-Json
  $m.status = "transcribed"
  $m | ConvertTo-Json -Depth 10 | Set-Content "A:\manifests_v6\$id.json" -Encoding UTF8
  ```
- **工作流單次擊發測試 (One-Shot 模式)**：
  不要讓 workflow 進入無限迴圈，使用 `--one-shot` 跑一次就停，方便檢查 Log：
  ```powershell
  python scripts_v6\run_workflow.py --one-shot
  ```
- **精準篩選特定任務的 Log 軌跡**：
  使用 `Select-String` 從龐大的日誌中抽出特定任務 ID 的執行紀錄：
  ```powershell
  ```powershell
  Select-String -Path A:\logs_v6\workflow.log -Pattern "task_xxx" | Select-Object -Last 15
  ```

### 6. 介面啟動與模組載入防護規範 (UI & Module Safeguards)
* **Streamlit 啟動語法與路徑固定**：絕對禁止自作聰明使用 `python -m streamlit run` 或隨意更改啟動路徑。必須嚴格照抄原版沙盒 `LexMind_V6_沙盒驗證版.ps1` 的寫法，使用 `Start-Process powershell` 搭配 `-NoExit` 及 `-Command "streamlit run app_v6.py"`，並確保 `WorkingDirectory` 為專案根目錄，否則會破壞 Streamlit 的模組載入機制與 `sys.path`。
* **管線斷裂與環境變數崩潰 (0x800700E8) 防護**：在啟動需要長駐的 Python 進程（如 Streamlit 或監控程式）時，必須先由父進程設定好環境變數（如 `PYTHONUTF8="1"` 與 `PYTHONIOENCODING="utf-8"`）供子進程繼承。若在 `-Command` 內部做複雜串接或漏設編碼，極易導致 I/O Pipe 斷裂而發生 0x800700e8 閃退。
* **Watchdog 模組名稱遮蔽盲點 (Name Shadowing)**：專案底下的 `scripts_v6\watchdog.py` 會與 pip 安裝的官方 `watchdog` 套件撞名。若啟動路徑錯誤，將導致 Streamlit 誤載入專案的腳本而崩潰。解法是嚴格固定在根目錄啟動，並在 `.streamlit/config.toml` 中強制設定 `fileWatcherType = "none"`。
* **儀表板背景殭屍進程遮蔽 (Dashboard Zombie Shadowing)**：`LexMind_V6_沙盒驗證版.ps1` 依賴 `CommandLine -match "progress_dashboard"` 判斷是否要開啟 PowerShell 監控視窗。若先前有 AI 或腳本在背景執行了 `python progress_dashboard.py` 且未正確關閉，啟動腳本會誤判儀表板已存在而跳過視窗彈出，導致使用者覺得「儀表板不見了也沒 Run 起來」。除錯時必須徹底 Taskkill 背景隱藏的 Python 進程。



### 7. 近期除錯三大核心錯誤總結 (Debug Retrospective)
使用者強烈要求記錄以下三大地雷，後續所有 Agent 必須牢記，嚴禁重蹈覆轍：
1. **「V6 是空殼」的假象 (Port Hijacking)**：過去曾有 AI 自作聰明撰寫 patch_streamlit.py，擅自修改啟動腳本將 localhost:8506 導向了 web_dashboard.py (原本在 7788 埠運行的純文字 HTTP 伺服器)，導致使用者打開瀏覽器卻只看到「LexMind-Omni Web 進度儀表板」的文字，誤以為 V6 的 pp_v6.py Streamlit 介面是空的。V6 絕非空殼，嚴禁擅自替換啟動埠與腳本綁定。
2. **config.toml 語法錯誤與重置問題**：先前的 AI 透過 API 直接用純文字模式 (無 UTF-8 BOM) 寫入 .streamlit/config.toml，導致 Windows PowerShell 解析時出現亂碼與 MissingEndCurlyBrace 語法錯誤，進而造成 Streamlit 只要有連線就會報錯崩潰並重置。所有設定檔與腳本寫入，必須確保符合 Windows 的編碼要求 (UTF-8 BOM)。
3. **儀表板消失不見 (Zombie PowerShell Loop)**：雖然先前的啟動腳本有 	askkill /F /IM python.exe，但背景監控儀表板 (如 progress_dashboard.py) 是被包在 powershell.exe -Command "while(true){...}" 的無窮迴圈內執行的。因此，單純殺掉 Python 進程後，外部的 PowerShell 會立刻在 5 秒後將其重生，導致背景永遠有一個無介面的殭屍 Dashboard 在跑。當新的啟動腳本偵測到 progress_dashboard 已存在時就會顯示 [SKIP] 跳過彈出視窗，讓使用者覺得「儀表板沒 Run 起來」。現已於 LexMind_V6_沙盒驗證版.ps1 實裝透過 WMI 抓取並摧毀這類隱藏 PowerShell 迴圈的機制 (Get-CimInstance Win32_Process)。

---

## 🚨 十、 系統最高防禦與開發 17 條鐵律 (The 17 Ironclad Rules)

為了防止外包的 Sub-Agent (如 QA、Coder) 因底層 LLM 幻覺而污染系統，並徹底杜絕「假專家」的過時建議，所有接手的 AI 代理人必須無條件遵守並在發包時夾帶以下 17 條鐵律：

### === 前 3 條：交接與發包鐵律 (Handoff & Delegation) ===
1. **未經允許，禁止刪改**：絕不准亂刪東西，也不准寫東西未經允許。
2. **先展示，後動作**：有任何大範圍刪減，必須先框起來給使用者看，獲得同意才能動手。
3. **嚴禁洗版與加時間戳記**：除錯交接素材必須存入實體檔案，檔名嚴禁加時間戳記，聊天室嚴禁印出超過 50 行程式碼。

### === 後 14 條：系統環境防崩潰、架構地雷與防禦紀律 (System Safeguards & Anti-Hallucination) ===
4. **禁止終端機輸出 Emoji**：Windows 預設 CP950 無法解析 Emoji，會導致進程卡死。
5. **純 ASCII 圖示安全化**：終端機提示僅限使用純 ASCII 符號（如 `[OK]`, `[WARN]`）。
6. **強制腳本編碼**：所有 Python/PowerShell 檔案必須強制使用 UTF-8 或 UTF-8-BOM 編碼。
7. **CP950 日誌讀取防護**：讀取 Windows 日誌時遇到中文字節易報錯，讀檔必須加 `errors="replace"` 或 `"ignore"`。
8. **字典取值 KeyError 防呆**：嚴禁硬抓 JSON 欄位，必須強制使用 `.get()` 方法。
9. **API 呼叫無聲死鎖防禦**：呼叫 API 時絕對不可漏設 `timeout`，避免 Worker 永久掛起。
10. **背景重啟 WinError 10106 防護**：隱藏視窗使用 `pythonw` 易因缺乏標準 I/O 崩潰，必須用正常 `python` 指令重定向標準輸出。
11. **KPI 監視器假死盲點**：連續 3 輪 (15分鐘) 產出為 0 即視為故障並強制重啟。
12. **金鑰輪替 Race Condition 防護**：遇到 429 時嚴禁抓全域金鑰，必須用發出請求的局部變數 `active_key`。
13. **例外退避機制的死角**：必須防無窮迴圈、加 Sleep 緩衝，並推送 Failed 狀態防幽靈進度。
14. **強制夾帶最高鐵律**：發包給 Sub-Agent 時，必須在 Prompt 結尾強制附上 17 條鐵律，嚴禁讓其無邊界發揮。
15. **嚴禁幽靈命名幻覺**：絕對不准 Sub-Agent 發明新的變數、路徑或腳本名稱，只能使用既定標準名稱。
16. **主 Agent 絕對守門與人工審查**：回傳的修復程式碼絕對禁止盲目貼上，主 Agent 必須親自逐行審查，確認無污染後才可寫入。
17. **永遠禁用 os.system 清空畫面 (防禦假專家)**：嚴禁無腦接受外部 AI 專家給的 `os.system("cls")` 建議。在背景高併發無窮迴圈中，這會引發嚴重的黑視窗閃爍災難，一律改用原生 ANSI 控制碼 `print("\033[H\033[J", end="")`。
