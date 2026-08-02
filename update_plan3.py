import os

plan_path = r'C:\Users\temp\.gemini\antigravity\brain\090c45c8-c66c-443a-b0a9-ac871eca1570\implementation_plan.md'

new_plan = """> [!WARNING]
> **【寫給接下來要接手或執行的 AI 的最高警告：程式碼審核 8 大鐵律】**
> 在這台 Windows 機器上，曾發生過嚴重的編碼與崩潰歷史。任何 AI 在寫程式，或接受別人給的程式碼準備貼上之前，**務必先檢查這 8 條規範**，否則將引發災難性崩潰：
> 1. **絕對禁止在 Terminal / PowerShell 輸出 Emoji 或非標準 Unicode 符號**：Windows 預設的 CP950 / Big5 編碼環境無法解析 Emoji，只要程式的 `print()` 或 `Write-Host` 中包含 Emoji（如 [WARN]、[OK] 等），會導致腳本当場崩潰 (UnicodeEncodeError) 甚至讓整個進程卡死。
> 2. **腳本編碼限定**：所有寫入的 Python (`.py`) 與 PowerShell (`.ps1`) 檔案，必須強制使用 `UTF-8` 或 `UTF-8-BOM` 編碼。
> 3. **終端機輸出安全化**：若有必要使用圖示，只能使用純 ASCII 符號（如 `[OK]`, `[WARN]`, `[FAIL]`, `[GUARD]` 等），絕不能為了美觀而擅加 Emoji。這已經發生過無數次血淚教訓，絕對不可再犯！
> 4. **字典取值的「引號」崩潰（KeyError 大爆炸）**：程式碼裡若大量寫死用 `manifest["task_id"]` 等去硬抓資料，只要讀到舊版或欄位缺失的 JSON 就當場噴錯死掉。必須強制使用防呆的 `manifest.get("task_id", "unknown_task")`。
> 5. **Vertex AI 無聲死鎖 (Deadlock 導致 1417 Chunks 卡死不動)**：呼叫 Vertex AI 等外部 API 時，絕對不可忘記設定 timeout（如 `http_options={'timeout': 120.0}`），否則伺服器一延遲，整個並行 Worker 會永遠掛起卡死。
> 6. **KPI 監視器的「假死」盲點**：進程活著不代表系統正常！KPI 邏輯必須強制規定「只要連續 3 輪 (15分鐘) Chunk 產出為 0，就視為實質故障並強制重啟」。
> 7. **讀取日誌的 CP950 編碼報錯 (0xa6 亂碼)**：在 Windows 讀日誌時，讀到中文字節 (0xa6) 會被預設 UTF-8 噴錯中斷，務必加上 `errors="replace"` 或 `errors="ignore"` 進行防護。
> 8. **背景自動重啟的瞬間閃退 (WinError 10106)**：為了隱藏視窗使用 `pythonw` 會導致非同步模組因缺乏標準 I/O 而瞬間崩潰。必須改回正常的 `python` 指令，並將 stdout/stderr 重定向到 `A:\\logs\\` 來維持背景重啟運作。

---

# LexMind-Omni 核心防護修改計畫書 (Merge & Restart)

## User Review Required
> [!IMPORTANT]
> 這是修補系統假死、工作流程停滯的重大架構變更，請長官詳細閱讀以下「修了什麼」以及「驗收方式」，確認無誤後再點擊 Proceed。

## 📌 1. 這版修了什麼 (Goal & Changes)
這版的修改是為了解決長期以來的「假死」與「假成功」障眼法，並提供全面的防護。

### 1.1 `merge_transcript.py` 的改造效果：
* **錯誤不外拋**：Merge 內未預期錯誤不再 raise 到 workflow engine。
* **Key 安全釋放**：不再到處手動 `release_key()`，而是統一走 `finally` 區塊，避免資源洩漏。
* **超時退避降級**：Reduce timeout 也會累積到全局降級門檻，避免死鎖。
* **全面 Guard 防護**：針對 `raw_chunks` 為空、`manifest/chunks` 為 None、`merged_cleaned_text` 為空等情況，都有完整的 guard。
* **小整理 (重複與未用 Import 清除)**：
  * 刪除重複的 import：`import sys`、`import json`、`import time`、`from pathlib import Path` 等重複宣告。
  * 刪除沒用到的 `io` (`import sys, io` 裡的 `io`)。

### 1.2 `restart_workflow.ps1` 的升級效果 (優先上線)：
* **驗證式重啟**：把「重啟」升級成真正的「驗證」。利用 `Start-Process ... -PassThru` 先拿到 PID，**等 6 秒後**再用 WMI 反查 `scripts_v6\\run_workflow.py` 是否還在。
* **直吐錯誤**：如果 6 秒後不在，就直接把 stderr/stdout 尾巴印出來並 throw，不再假裝成功。（解決了過去即使 Python 一進去就炸，畫面還是印綠字成功的問題）。
* **追加保護**：刪除 `workflow.lock` 及清除 `quota_state.json` 之前都會先備份 (`.bak`)。

---

## 📌 2. 驗收方式 (Verification Plan)
修改完成後，必須驗證以下 4 個結果，確保系統行為符合預期：

### 2.1 Merge 的驗收
1. **日誌正確降級**：當 Merge 發生 timeout 時，log 應該出現「觸發全局 raw_fallback」或「emergency raw_fallback」，而不是上拋成「Merge step failed」。
2. **流程不斷鏈**：workflow process **不應**因這支檔案內的 merge 失敗而直接消失。
3. **任務狀態明確**：manifest 應該要嘛成功 `merged`，要嘛安全退回 `chunked`，不應停在半殘狀態。
4. **兜底檔案產出**：`merged_full_transcript.txt` 與 `merged_cleaned_transcript.txt` 至少能在 fallback 情況下被寫出來，不會憑空消失。

### 2.2 Restart 的驗收
* 驗證在 `scripts_v6\\run_workflow.py` 有語法錯誤或無法正常啟動的情況下，執行 `restart_workflow.ps1` 必須在 6 秒後於終端機直接打印出 `[FAIL]` 與 stderr 的尾巴，並丟出 Exception 中止，不可繼續顯示 `[START]` 假象。

---

## 📌 3. 待替換程式碼 (Proposed Changes)
以下是準備套用防護機制的檔案。

### 核心腳本

#### [MODIFY] [merge_transcript.py](file:///C:/LocalAI_Workstation/scripts_v6/merge_transcript.py)
* 將套用 try-catch 安全包裝、finally key release，並清除 `sys`, `json`, `time`, `Path`, `io` 等重複引用。

#### [MODIFY] [restart_workflow.ps1](file:///C:/LocalAI_Workstation/restart_workflow.ps1)
* 將升級為 WMI 驗證重啟，並追加鎖檔與 Quota 備份保護。
"""

with open(plan_path, 'w', encoding='utf-8') as f:
    f.write(new_plan)

print('Plan rewritten successfully.')
