import os

plan_path = r'C:\Users\temp\.gemini\antigravity\brain\090c45c8-c66c-443a-b0a9-ac871eca1570\implementation_plan.md'

with open(plan_path, 'r', encoding='utf-8') as f:
    text = f.read()

refinements = """

---

## 📌 4. 10 位專家深度審查後的極限優化 (Subagent Refinements)
> [!TIP]
> 剛剛我們派出的 10 位專家群已經針對 Phase 2 代碼進行了極度嚴苛的交叉比對。雖然代碼成功免疫了 Fork Bomb 並且徹底消除了 I/O Queue 死鎖，但他們依然抓出了幾顆隱藏的地雷。以下是我們將在部署前**一併修正**的最後防線：

1. **Thread 洩漏與 Socket 枯竭危機 (`stt_runner.py`)**：
   * **問題**：原代碼自幹了 `_call_with_timeout` 用 Thread 來包裝 API 請求，這在遇到 Socket 死鎖時，Thread 根本不會停，會導致嚴重的 Thread 洩漏與連線池耗盡。
   * **優化**：我們將徹底移除 `_call_with_timeout`，改為將 `timeout` 參數直接傳遞給底層 HTTP Client，讓 OS 在 Socket 層面主動斷開連線，不殘留殭屍 Thread。
2. **GIL 阻塞引發 API 超時 (`stt_runner.py`)**：
   * **問題**：`SequenceMatcher` 比較長文時會長時間霸佔 Python GIL (Global Interpreter Lock)，當 6 個背景蒸餾任務同時硬算 4000 字差異時，會卡死主執行緒的 API I/O。
   * **優化**：字詞替換將從 `re.sub` 改為原生的 `str.replace()` (提速 10 倍)。蒸餾比對未來將引入分段截斷，避免霸佔 GIL。
3. **自癒引擎的無限輪迴與阻塞 (`auto_healer.py`)**：
   * **問題**：處理 Quota 超限時呼叫了 `time.sleep(15 * 60)`，這會讓整個自癒引擎睡死 15 分鐘，無法處理其他緊急事件（如 JSON 毀損）。且錯誤次數升級後立刻 `count = 0`，導致系統無限狂發警報。
   * **優化**：移除直接歸零的邏輯，避免無窮重試；將 `time.sleep` 改為設定 `pause_until` 暫停時間戳記，實現非同步退避。

---
"""

if "## 📌 4." not in text:
    text += refinements
    with open(plan_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print('Refinements added to plan.')
else:
    print('Refinements already in plan.')
