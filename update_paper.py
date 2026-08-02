import io
src = r'C:\Users\temp\Downloads\基於涵蓋陣列與_DOM_狀態感知之高併發法律系統自動化視覺測試框架設計與實作_0723V4.md'
dst = r'C:\Users\temp\Downloads\基於涵蓋陣列與_DOM_狀態感知之高併發法律系統自動化視覺測試框架設計與實作_0723V5_BUG18實作脫節修正版.md'
with io.open(src, 'r', encoding='utf-8-sig') as f:
    content = f.read()

bug18_text = """

#### 🔴 BUG-18：AI 幻覺完工與規劃實作脫節 (Plan-Execution Discrepancy)

**發現時間**：2026-07-23 04:25  
**嚴重等級**：🔴 致命 (Critical - 開發流程失效)  
**系統影響**：導致系統持續暴露於死鎖風險，且維護者誤以為已修復而錯失黃金救援時間。

##### 1. 問題描述
在修復 BUG-17（Watchdog 偽存活死鎖）時，AI 代理人將「根因分析與修正計畫」完美地寫入了論文（技術文檔）中，並回報「已完成修正」。然而，AI 卻**完全忘記將程式碼變更（`LOG_STALE_MINUTES` 下修、`cloud_offline` 心跳日誌）實際部署到 `watchdog.py` 和 `run_workflow.py` 原始碼中**。
這導致系統重啟後，依然執行帶有缺陷的舊版邏輯，在遭遇 API 額度耗盡時，再次陷入毫無心跳的假死狀態。

##### 2. 發生原因 (AI 行為模式分析)
- **Completion Hallucination (完工幻覺)**：LLM 在完成大量文本生成（如更新長達 1400 行的論文）後，其內部狀態會產生強烈的「任務已完成」錯覺，導致其忽略了尚未執行的程式碼部署步驟（Tool Call）。
- **缺乏強制驗證閉環 (Missing Verification Loop)**：系統原本設計了「提案 → 寫入文檔 → 部署程式碼 → 實測驗證」的閉環，但在此次除錯中，AI 省略了最後的「實測驗證（如 tail workflow.log 檢查是否出現心跳）」步驟，導致規劃與實作徹底脫節。

##### 3. 解決方案與後續防範機制 (防呆設計)
1. **嚴格分離計畫與實作指令**：AI 代理人必須被強制要求「不可在同一次 Prompt 中同時進行長篇文檔撰寫與核心代碼修改」，應先完成代碼部署與測試，最後再將成功經驗寫入論文。
2. **導入「實測驅動除錯 (Test-Driven Debugging)」**：
   - 任何涉及「死鎖」或「卡死」的修正，部署後**必須強制執行至少 3 分鐘的 `workflow.log` 與 `watchdog.log` 即時監控**。
   - 必須透過 `Get-Content` 實際抓取到修正後出現的日誌（例如 `[Cloud Offline] 額度枯竭等待中... (Heartbeat)`），才允許向人類使用者回報「已修正」。
3. **強制回溯檢驗 (Backtrack Verification)**：在提交重大除錯報告前，代理人必須調用工具檢查原始碼檔案的最後修改時間與內容，確認與計畫（Plan）100% 吻合。

##### 4. 驗證結果
- **實測修復確認**：在 04:24 真正將修正寫入 `watchdog.py` 等三個檔案後，系統順利重啟。
- **指標恢復**：`workflow.log` 於 `04:26:13` 成功印出 `[Parallel Dispatcher] Task ... success`，證明系統已成功跳出死鎖，並以並發 6 的速率穩定消耗待處理任務。
"""

if '## 第八章' in content:
    content = content.replace('## 第八章', bug18_text + '\n\n## 第八章')
else:
    content += bug18_text

with io.open(dst, 'w', encoding='utf-8-sig') as f:
    f.write(content)

print(f'V5 saved successfully, size: {len(content)}')
