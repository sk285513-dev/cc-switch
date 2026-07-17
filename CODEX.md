# CODEX.md — 程式碼規範與開發標準
C1. 工具鏈標準

本專案以 Python 3.12+（後端 AI 邏輯）與 TypeScript/Node.js 22（前端與 API 閘道）為雙語言架構。所有程式碼合併前須通過以下工具鏈：

工具

語言

最低標準

ruff

Python

零 error，零 warning

mypy --strict

Python

零 type error

bandit -ll

Python

零 high/medium security issue

eslint

TypeScript

零 error

tsc --noEmit

TypeScript

零 compile error

pytest

Python

覆蓋率 ≥ 85%，46 個測試案例全通過

C2. 命名規範

Python 模組使用 snake_case，法律領域模組以 legal_ 為前綴。TypeScript 元件使用 PascalCase，API 路由使用 kebab-case（如 /api/scan-local-media）。Agent 類別以 Agent 結尾，評測器以 Evaluator 結尾，Skill 以 Skill 結尾。

C3. 法律 AI 特殊規範

引用完整性原則：所有生成的法律文本必須附帶可驗證的條文引用，禁止使用「依相關法規」等模糊表述。每個引用必須包含：法典名稱、條號、項次（如有）、生效版本。

幻覺防護原則：所有法律條文的生成必須經過 CitationVerificationAgent 的驗證，驗證失敗的回應必須標記 UNVERIFIED 並附帶警告說明，嚴禁直接輸出未驗證的法律引用。

時效敏感性原則：涉及消滅時效、除斥期間的計算必須使用 DeadlineCalendar 的知識庫（src/legal_kb/limitation_periods.py），禁止 LLM 自行計算時效，Hard Gate 閾值為零容忍（= 1.00）。

視窗代碼輸出禁令：嚴禁在聊天對話視窗輸出超過 50 行的完整程式碼區塊，防止 KV Cache 爆炸。所有程式碼變更必須靜默呼叫原生檔案寫入工具處理。

資料最小化原則：日誌中禁止記錄姓名、身分證字號、案件當事人等敏感資訊，統一以 [REDACTED] 替代。

C4. Git 提交規範

feat(agent-①): 新增糾錯排版功能

fix(eval-gate): 修復幻覺率計算邏輯

perf(vector): HNSW 索引效能優化

test(gates): 新增時效計算測試案例

skill(s03): 更新 limitation-calculator Skill

docs(api): 更新 OpenAPI 規格

C5. 除錯回滾協議

若連續 3 輪除錯 Bug 未減或發生錯誤漂移，必須執行 Git Rollback 退回安全綠色節點：

git log --oneline -10 # 查看最近 10 個提交

git rollback <safe-commit-sha> # 退回安全節點