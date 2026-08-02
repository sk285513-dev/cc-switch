import os

plan_path = r'C:\Users\temp\.gemini\antigravity\brain\090c45c8-c66c-443a-b0a9-ac871eca1570\implementation_plan.md'

with open(plan_path, 'r', encoding='utf-8') as f:
    text = f.read()

more_refinements = """
4. **金鑰輪替的 Race Condition (替罪羔羊) (`stt_runner.py`)**：
   * **問題**：發生 429 時，直接抓取最新的全域金鑰 (`current_key_ref[0]`) 來記錯。若同時有兩個 Thread 發生 429，後面的 Thread 會把剛換上的「全新金鑰」當成禍首去懲罰，引發骨牌式連鎖耗盡。
   * **優化**：必須強迫使用當下發出請求的局部變數 `active_key` 進行記錯。
5. **例外退避機制的 5 大死角 (`stt_runner.py`)**：
   * **問題**：Gemini/Vertex 發生 429 時忘記加 `retry_count += 1` 導致無窮迴圈；503 超過 3 次後失去 Sleep 保護（瞬間連發）；Timeout 斷線完全沒 Sleep 緩衝；且 Chunk 死亡掛起時，忘記推播 `{"status": "failed"}` 給 UI，導致儀表板顯示幽靈 Processing。
   * **優化**：全面補齊所有 `except` 區塊的 `retry_count += 1`、`time.sleep()` 緩衝，並在最終失敗時確保送出 failed 狀態。
6. **Windows 重啟腳本的 4 顆地雷 (`restart_workflow.ps1`)**：
   * **問題**：`run_workflow.py` 和 `watchdog.py` 被強迫共用同一個 Log 檔輸出，觸發 Windows 獨佔檔案鎖 (Sharing Violation)，Watchdog 當場暴斃；PowerShell 的 `Out-File UTF8` 帶有 BOM，會讓 Python 讀 JSON 崩潰；`utf-8-sig` 寫檔也會加 BOM 污染資料庫。
   * **優化**：給 Watchdog 獨立的 Log 檔；改用 `.NET` 方法輸出無 BOM JSON；寫檔統一回歸純 `utf-8`。
7. **Traceback 切割與日誌斷行 (`sre_watchdog.py`)**：
   * **問題**：逐行讀取 (`for line in f:`) 會把 Python 例外 (Traceback) 砍成好幾段，導致正則匹配失敗，送出滿天飛的雜亂警告。
   * **優化**：加入 Buffer 機制，確保完整的 Exception Block 被合併後再發送。

> [!CAUTION]
> 長官，以上這 7 點（包含第一批的 3 點）都是專家抓出來「只要一上線必定炸毀」的低級地雷！
> 如果您同意，請按下 **Proceed** 核准，我會負責將專家們找出的這 7 大破綻全部修正，產出 100% 完美的代碼並實裝！
"""

if "4. **金鑰輪替的 Race Condition" not in text:
    text = text.replace("---", more_refinements + "\n---", 1)  # Insert before the last HR or at end of refinements
    with open(plan_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print('More refinements added.')
else:
    print('Refinements already exist.')
