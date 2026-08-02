import os
import re

file_path = r'C:\Users\temp\.gemini\antigravity\brain\9ccc4726-3ac1-4fe6-bcb7-aa2c09335f30\original_135_plan.md'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

insert_text = """
### 9. 災難復原：檔名注入 DoS 防禦 (優先實作)
* [ 實作方式: 自行開發 | 外部相依: google.api_core.exceptions | 專家諮詢: 無須 ]
* **系統分析架構可視圖 (修改說明)**:
  + 在 7/25 退版後，quota_manager.py 的異常比對邏輯退回了粗糙的字串比對 ("429" in err)。這會導致如果有檔案名稱叫做 429_quota.wav 發生讀取錯誤時，系統會誤以為是 API 額度耗盡，進而錯誤拉黑健康的金鑰。
  + **修改策略**：引入嚴謹的 isinstance 型別檢查，捕捉原生的 google.api_core.exceptions.ResourceExhausted。
  + **風險評估**：極低。僅修改 Exceptions 捕捉邏輯，不影響主工作流。
* **修改前程式碼 (BEFORE)**:
  `python
  is_429 = "429" in safe_err_msg
  `
* **修改後程式碼 (AFTER)**:
  `python
  import google.api_core.exceptions as google_exceptions
  is_429 = isinstance(e, google_exceptions.ResourceExhausted) or getattr(e, 'code', None) == 429
  `

### 10. 災難復原：RAM 監控防護與 OOM 預防 (優先實作)
* [ 實作方式: 自行開發 | 外部相依: psutil | 專家諮詢: 無須 ]
* **系統分析架構可視圖 (修改說明)**:
  + 系統在進行高併發 STT 或 OpenCV 黑板辨識時，記憶體常會飆高。若未踩煞車，會觸發 SSD 虛擬記憶體 Swap，導致全機 IO 假死。
  + **修改策略**：在背景監控的 sre_watchdog.py 中，加入 psutil.virtual_memory() 的監控，當 RAM 負載突破 92% 時，強制斬殺最佔資源的殭屍進程以自保。
  + **風險評估**：極低。屬於獨立背景監控程式，不會干預正常跑在 80% RAM 以下的任務。
* **修改前程式碼 (BEFORE)**:
  `python
  # sre_watchdog.py 缺乏記憶體監控，僅監控進程時間
  `
* **修改後程式碼 (AFTER)**:
  `python
  import psutil
  mem = psutil.virtual_memory()
  if mem.percent >= 92.0:
      print(f"[Watchdog Alert] RAM 負載過高 ({mem.percent}%)！預防性斬殺防當機...")
      # 執行殭屍進程清理邏輯
  `

"""

if "### 9. 災難復原" not in content:
    content = content.replace("## 第六部分", insert_text + "\n## 第六部分")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully appended to original_135_plan.md")
else:
    print("Already inserted")
