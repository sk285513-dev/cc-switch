import os

plan_path = r'C:\Users\temp\.gemini\antigravity\brain\090c45c8-c66c-443a-b0a9-ac871eca1570\implementation_plan.md'

with open(plan_path, 'r', encoding='utf-8') as f:
    text = f.read()

background_info = """
## 📌 0. 背景資訊與日誌 (Background Context & Logs)
這份計畫書是為了解決我們今天一整天都在除錯的核心問題。不了解這些背景，後續接手的 AI 將無法審核這份程式碼的目的。

### 🚨 遇到的具體症狀與日誌 (Bug 說明)
1. **Workflow Process 無聲消失 (卡死停滯)**：
   * 症狀：畫面停在「1417 Chunks / 1452 Chunks」，進度條完全卡死不動，但沒有噴出任何明顯錯誤。
   * 真因：`merge_transcript.py` 在呼叫 Vertex AI (Gemini) 時，因為沒有設定 `timeout`。當伺服器延遲時，整個並行 Worker 就會死鎖 (Deadlock)。且當拋出例外時，錯誤一路往上 `raise` 給 workflow 引擎，導致主程式崩潰消失，但任務狀態卻停在半殘狀態（沒有成功，也沒有退回 chunked）。
2. **API 金鑰假性耗盡 (資源洩漏)**：
   * 症狀：日誌中出現「無法取得排他性 API 金鑰」，但其實根本沒有人在跑。
   * 真因：舊版程式碼在拋出 Exception 時，沒有使用 `finally` 區塊來執行 `release_key()`，導致金鑰被永遠鎖死。
3. **假重啟 (Restart 腳本盲點)**：
   * 症狀：只要一有問題，執行 `restart_workflow.ps1` 時終端機總是印出綠字的 `[START] run_workflow.py launched`，讓開發者以為系統已經恢復。但事實上，Python 進程可能在 1 秒內就因為 `import` 錯誤或編碼錯誤死掉了（例如 WinError 10106 或 CP950 錯誤）。
   * 真因：舊版 `restart_workflow.ps1` 只是單純把指令送出，並沒有驗證進程是否真的存活，嚴重誤導 Debug 方向。

---
"""

# Find where to insert this (right before '## User Review Required')
insert_point = "## User Review Required"
if insert_point in text:
    text = text.replace(insert_point, background_info + "\\n" + insert_point)

with open(plan_path, 'w', encoding='utf-8') as f:
    f.write(text)

print('Background context added to plan successfully.')
