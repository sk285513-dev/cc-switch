import sys
path = r'C:\Users\temp\antigravity\LexMind-Omni-法律實務-AI-工作站\.agents\AGENTS.md'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

target = '''> **【寫給所有未來準備撰寫計畫書的 AI 的最高警告】**
> 不管你要寫的計畫書有多大或多小，**在計畫書的最開頭，必須強制列出「這台機器曾經發生過的編碼問題與錯誤歷史清單」**。
> 你必須先提醒自己與接下來要接手的 AI：注意哪些編碼能用、哪些不能用（例如：絕對禁止在終端機輸出 Emoji 或 Unicode 符號，否則會觸發 Windows CP950 崩潰）。必須在寫程式或發包前先過濾掉這些毒瘤。
> 絕對禁止再犯這些問題！即使計畫寫完了，也必須再三檢查，確保計畫內容本身沒有帶有 Emoji 等編碼地雷。'''

target_crlf = target.replace('\n', '\r\n')
target_lf = target

replacement = '''> **【寫給所有未來準備撰寫計畫書的 AI 的最高警告：程式碼審核 8 大鐵律】**
> 不管你要寫的計畫書有多大或多小，在計畫書的最開頭，必須強制列出「這台機器曾經發生過的血淚地雷清單（包含編碼與系統架構缺陷）」。任何 AI 在寫程式，或接受別人給的程式碼準備貼上之前，**務必先檢查這 8 條規範**，否則將引發災難性崩潰：
> 1. **絕對禁止在 Terminal / PowerShell 輸出 Emoji 或非標準 Unicode 符號**：Windows 預設的 CP950 / Big5 編碼環境無法解析 Emoji，只要程式的 print() 或 Write-Host 中包含 Emoji（如 [WARN]、[OK] 等），會導致腳本当場崩潰 (UnicodeEncodeError) 甚至讓整個進程卡死。
> 2. **腳本編碼限定**：所有寫入的 Python (.py) 與 PowerShell (.ps1) 檔案，必須強制使用 UTF-8 或 UTF-8-BOM 編碼。
> 3. **終端機輸出安全化**：若有必要使用圖示，只能使用純 ASCII 符號（如 [OK], [WARN], [FAIL], [GUARD] 等），絕不能為了美觀而擅加 Emoji。這已經發生過無數次血淚教訓，絕對不可再犯！
> 4. **字典取值的「引號」崩潰（KeyError 大爆炸）**：程式碼裡若大量寫死用 manifest["task_id"] 等去硬抓資料，只要讀到舊版或欄位缺失的 JSON 就當場噴錯死掉。必須強制使用防呆的 manifest.get("task_id", "unknown_task")。
> 5. **Vertex AI 無聲死鎖 (Deadlock 導致 1417 Chunks 卡死不動)**：呼叫 Vertex AI 等外部 API 時，絕對不可忘記設定 timeout（如 http_options={'timeout': 120.0}），否則伺服器一延遲，整個並行 Worker 會永遠掛起卡死。
> 6. **KPI 監視器的「假死」盲點**：進程活著不代表系統正常！KPI 邏輯必須強制規定「只要連續 3 輪 (15分鐘) Chunk 產出為 0，就視為實質故障並強制重啟」。
> 7. **讀取日誌的 CP950 編碼報錯 (0xa6 亂碼)**：在 Windows 讀日誌時，讀到中文字節 (0xa6) 會被預設 UTF-8 噴錯中斷，務必加上 errors="replace" 或 errors="ignore" 進行防護。
> 8. **背景自動重啟的瞬間閃退 (WinError 10106)**：為了隱藏視窗使用 pythonw 會導致非同步模組因缺乏標準 I/O 而瞬間崩潰。必須改回正常的 python 指令，並將 stdout/stderr 重定向到 A:\\logs\\ 來維持背景重啟運作。'''

if target_crlf in text:
    text = text.replace(target_crlf, replacement.replace('\n', '\r\n'))
    print('Replaced CRLF')
elif target_lf in text:
    text = text.replace(target_lf, replacement)
    print('Replaced LF')
else:
    print('Not found')
    sys.exit(1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
print('Done')
