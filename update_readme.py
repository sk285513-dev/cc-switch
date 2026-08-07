import sys
path = r'C:\Users\temp\antigravity\LexMind-Omni-法律實務-AI-工作站\README_DEVEL.md'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

target = '''> **【寫給所有未來準備撰寫計畫書的 AI 的最高警告】**
> 不管你要寫的計畫書有多大或多小，**在計畫書的最開頭，必須強制列出「這台機器曾經發生過的血淚地雷清單（包含編碼與系統架構缺陷）」**。
> 你必須先提醒自己與接下來要接手的 AI：
> 1. **終端機 Emoji 崩潰**：絕對禁止在 Python 的 print() 輸出 Emoji (如 ✅, ❌) 或 Unicode 特殊符號。必須全部使用 ASCII (如 [OK], [FAIL])，否則觸發 CP950 崩潰。
> 2. **字典取值的「引號」崩潰 (KeyError)**：嚴禁寫死使用 manifest["task_id"]。若 JSON 缺欄位會直接崩潰。必須統一使用防呆的 .get("task_id", "unknown")。
> 3. **外部 API 無聲死鎖**：呼叫外部服務 (如 Vertex AI) 絕對不可不設 Timeout。必須強制設定 timeout=120.0 等超時機制與降級邏輯。
> 4. **KPI 監視器的「假死」盲點**：嚴禁只用「進程存活與否」判定系統健康。必須檢查「實質產能」（連 15 分鐘 Chunk 產出為 0 即視為實質故障並重啟）。
> 5. **讀取系統輸出的 CP950 解碼報錯 (0xa6)**：呼叫系統指令或讀取 Windows 日誌時，必須加上 encoding="utf-8", errors="replace" 否則必遇 0xa6 亂碼中斷。
> 6. **背景自動重啟瞬間閃退 (WinError 10106)**：背景排程嚴禁濫用 pythonw 來隱藏視窗，必須使用標準 python 並將日誌確實重定向。
> 
> 絕對禁止再犯這些問題！即使計畫寫完了，也必須再三檢查，確保計畫內容本身沒有自帶編碼地雷。'''

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
