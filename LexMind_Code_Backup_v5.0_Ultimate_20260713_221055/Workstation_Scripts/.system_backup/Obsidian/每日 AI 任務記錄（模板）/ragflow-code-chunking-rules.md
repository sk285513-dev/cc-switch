# RAGFlow 程式碼資料集 Chunking 規則表

> 適用對象：16G VRAM 本地研究型 AI / coding agent / bugfix workflow
> 資料型態：Python / PowerShell / 日誌（log / stack trace）

---

tags:
  - ragflow
  - chunking
  - code-rag
  - python
  - powershell
  - logs
created: 2026-06-10
updated: 2026-06-10
status: v1

---

## 核心原則

程式碼資料的 chunking 不能只用固定字數，必須盡量對齊「語意單位」。對 code RAG 來說，最實用的策略是 **邊界導向 + semantic chunking + parent-child retrieval**：先保留函式 / class / 區塊邊界，再在過長內容內做次級切分，最後讓檢索用 child chunk、回答用 parent chunk。[web:2386][web:2388][web:2394]

RAGFlow 支援更結構感知的 chunking，以及 parent-child 機制，因此比單純每 N 字切一塊更適合處理程式碼、設定檔與錯誤日誌。[web:2386][web:2389]

---

## 總表

| 資料型態 | 主切塊邊界 | 次切塊條件 | Parent Chunk | Child Chunk | Keyword Weight | Rerank | 重點用途 |
|---|---|---|---|---|---:|---|---|
| Python | function / class / module section | 函式過長、類別過大時再切 | class / function 全文 [web:2386] | 內部邏輯段、方法段 [web:2386] | 中高 | 視任務開 | bugfix、找相似實作、架構理解 |
| PowerShell | function / param block / try-catch / pipeline | script 過長、單函式過長時再切 | function / script section 全文 [web:2386] | 區段、條件流、命令鏈 | 高 | 視任務開 | 自動化腳本維護、命令追蹤 |
| 日誌 / Stack Trace | 單次事件 / 單次錯誤鏈 / 時間區段 | trace 過長或混多事件才切 | 單次完整錯誤事件 [web:2387] | stack frame 群組 / error block | 高 | 建議開 | 錯誤分析、根因定位、過去案例召回 |

---

## 1. Python 資料集規則

### 最佳主切塊邊界

Python 的自然語意單位通常是：

- `function`
- `class`
- 模組內的大段設定 / helper 區
- `try/except` 錯誤處理區
- 測試檔中的單一 test case 群組

因此，**優先以函式與 class 當主切塊邊界**，不要把一個函式從中間切斷。[web:2388][web:2390]

### 次切塊條件

只有在以下情況才二次切分：

- 單一函式太長。  
- 單一 class 含太多方法。  
- 一段模組設定包含太多不相關子區塊。

此時可以把一個 parent chunk 再切成：
- 初始化區  
- 核心邏輯區  
- I/O 區  
- 錯誤處理區

### 建議 metadata

每個 Python chunk 建議保留：

- `file_path`
- `language=python`
- `symbol_type=function|class|module|test`
- `symbol_name`
- `module_name`
- `is_test`

### 不建議做法

- 每 300–500 字固定硬切。  
- 把 import、函式本體、例外處理拆到不同 chunk。  
- 把多個不相關函式合併成一塊。

### 適合查詢

- 「哪個函式在處理 RAGFlow 啟動流程」
- 「過去哪段 Python 有寫過 host.docker.internal 的 API 呼叫」
- 「這個 error handling pattern 在哪裡出現過」

---

## 2. PowerShell 資料集規則

### 最佳主切塊邊界

PowerShell 腳本的語意單位通常不只是 function，還包括：

- `function`
- `param()` 區塊
- `try/catch`
- 一整段 pipeline
- 明顯獨立的操作區段（例如：檢查環境、下載檔案、啟動服務）

因此，**PowerShell 應以 function 與明確腳本段落為主切塊邊界**。[web:2388][web:2390]

### 次切塊條件

當單一腳本很長時，可依流程切成：

- 前置檢查區  
- 下載 / 安裝區  
- 設定檔處理區  
- 啟動服務區  
- 驗證與錯誤處理區

如果某個 function 過長，再往內切成：
- 參數處理  
- 執行命令鏈  
- 例外處理

### 建議 metadata

每個 PowerShell chunk 建議保留：

- `file_path`
- `language=powershell`
- `symbol_type=function|script_section|pipeline|config`
- `symbol_name`
- `uses_docker`
- `uses_ollama`
- `uses_network`

### 不建議做法

- 把整支 `.ps1` 當一個 chunk。  
- 把 `try/catch` 切開。  
- 把一段命令鏈中間斷掉，導致命令關係失真。

### 適合查詢

- 「哪段 PowerShell 在檢查 Ollama 是否啟動」
- 「哪支腳本有處理 docker compose 啟動」
- 「過去如何在 PowerShell 裡自動修改 .env 檔」

---

## 3. 日誌 / Stack Trace 資料集規則

### 最佳主切塊邊界

日誌最重要的不是語法，而是事件完整性。對 log / stack trace，最好的主切塊邊界是：

- 單次錯誤事件  
- 單次 stack trace  
- 同一時間窗內的一組相關 log  
- 同一個 request / task id 的完整過程

如果一個 trace 被切斷，模型往往就抓不到因果鏈。[web:2387]

### 次切塊條件

只有在以下情況才往內切：

- 一個 trace 太長。  
- 一個 log 檔混了多次事件。  
- 同一段 log 同時包含啟動、錯誤、重試、結束多種狀態。

這時可拆成：
- 錯誤摘要區  
- stack frame 區  
- 相關前置 log 區  
- 重試 / 後續結果區

### 建議 metadata

每個 log chunk 建議保留：

- `file_path`
- `language=log`
- `log_type=runtime|error|stacktrace|service`
- `timestamp_start`
- `timestamp_end`
- `error_code`
- `exception_name`
- `service_name`
- `task_id` 或 `request_id`

### 不建議做法

- 每 500 字硬切。  
- 把 stack trace 的上半段和下半段拆開。  
- 不保留時間資訊與錯誤代碼。

### 適合查詢

- 「這次 RAGFlow 啟動失敗和之前哪次 log 最像」
- 「哪個例外在過去最常出現在 Docker 啟動階段」
- 「這個 request id 的完整錯誤鏈是什麼」

---

## Parent-Child 建議

| 資料型態 | Parent Chunk 建議 | Child Chunk 建議 |
|---|---|---|
| Python | 整個 function / class / test block [web:2386] | 內部邏輯段、方法段、錯誤處理段 |
| PowerShell | 整個 function / script section [web:2386] | pipeline 段、檢查段、設定段、啟動段 |
| 日誌 | 單次完整事件 / stack trace [web:2387] | stack frame 群組、前置摘要、後續處理段 |

這種做法的重點是：**用 child 提高召回精度，用 parent 保留上下文完整性。**[web:2386]

---

## 檢索參數建議

| 資料型態 | Similarity Threshold | Top N | Keyword Weight | Rerank |
|---|---:|---:|---:|---|
| Python | 0.12–0.20 [web:2377] | 4–6 [web:2377] | 中高 | 可開 |
| PowerShell | 0.10–0.18 [web:2377] | 4–6 [web:2377] | 高 | 可開 |
| 日誌 | 0.10–0.15 [web:2377] | 5–8 [web:2377] | 高 | 建議開 [web:2377] |

理由很簡單：程式碼與日誌都高度依賴函式名、檔名、錯誤碼、exception 類型，因此 keyword matching 必須保有較高權重。[web:2377][web:2380]

---

## 最佳實作順序

1. 先把 Python / PowerShell / log 分成三個資料集。  
2. 各自套不同 chunking 規則，不共用。  
3. 開 parent-child retrieval。 [web:2386]  
4. Hybrid search 一律開啟。 [web:2383]  
5. 先用真實 bugfix 問題做 retrieval test，再回頭微調 threshold / top N。[web:2383][web:2377]

---

## 一句話版本

- **Python：以函式 / class 為核心。**  
- **PowerShell：以 function / script section / pipeline 為核心。**  
- **日誌：以單次完整錯誤事件為核心。**

只要 chunk 對齊這些語意單位，RAGFlow 在 code retrieval 上就會比固定字數切塊穩定得多。[web:2388][web:2394]

