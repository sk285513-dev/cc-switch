# 本地研發型 AI 最大架構圖：哪些層用現成、哪些層自己客製

> 適用場景：Windows + RTX 5060 Ti 16GB + 本地模型 + 研發 / coding / 研究分析型 AI 系統

---

tags:
  - local-ai
  - architecture
  - coding-agent
  - rag
  - obsidian
  - windows
created: 2026-06-10
updated: 2026-06-10
status: 規劃中

---

## 一句話原則

**底層盡量用現成；越靠近你的工作流、資料、規則、決策邊界，越要自己客製。**

也就是說，不要自己重造聊天 UI、模型伺服器、基本 agent loop；但要自己定義你的工具層、專案規則、驗證流程、長期記憶與研究任務模板。[web:2302][web:2305][web:2306]

---

## 最大架構圖

```text
┌─────────────────────────────────────────────────────────────┐
│  A. 使用者互動層（Human Interface Layer）                    │
│  ├─ 現成：OpenHands / Open WebUI / Jan / LM Studio          │
│  └─ 客製：你的任務模板、中文提示詞、專案入口                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  B. Agent 協作與工作流層（Agent / Workflow Layer）            │
│  ├─ 現成：OpenHands / LangGraph / CrewAI / OpenClaw         │
│  └─ 客製：研究流程、coding workflow、judge 規則、任務拆解      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  C. RAG / 記憶 / 檢索層（Retrieval Layer）                    │
│  ├─ 現成：RAGFlow / R2R / AnythingLLM / 向量庫 / BM25         │
│  └─ 客製：chunking 規則、資料分類、Obsidian 筆記結構          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  D. 工具執行層（Tool Execution Layer）                        │
│  ├─ 現成：Shell / Python / Git / Docker / Browser tools      │
│  └─ 客製：PowerShell 橋接、Windows GUI、自動測試、回滾邏輯     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  E. 本地模型推理層（Model Serving Layer）                     │
│  ├─ 現成：Ollama / vLLM / LM Studio backend                  │
│  └─ 客製：模型分工策略（Gemma / Qwen / DeepSeek）             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  F. 基礎設施層（Infra Layer）                                 │
│  ├─ 現成：Windows / WSL / Docker / Python venv / uv          │
│  └─ 客製：資料夾規範、權限邊界、排程、備份與日誌保留策略         │
└─────────────────────────────────────────────────────────────┘
```

---

## 分層說明

## A. 使用者互動層

### 建議：**以現成為主，只做薄客製**

這一層不要自己重做。UI、基本聊天視窗、檔案拖放、多分頁會話、模型切換，這些都應該直接使用現成工具，例如 OpenHands、Open WebUI、Jan、LM Studio。[web:2286][web:2269][web:2270]

### 自己要客製什麼

- 中文任務入口。
- 你的常用 prompt 按鈕。
- 「研究分析」「coding 任務」「文件摘要」三種入口模板。
- 與 Obsidian / 任務日誌的快捷入口。

### 不要自己做什麼

- 聊天 UI。
- 檔案上傳小部件。
- 一般對話歷史系統。

---

## B. Agent 協作與工作流層

### 建議：**現成框架 + 自己定義流程**

這是整個系統最重要的一層。Agent 框架本身可以用現成的，例如 OpenHands、LangGraph、CrewAI 或 OpenClaw，但你的工作流不能完全照抄別人，因為研究分析與 coding 任務的步驟不同。[web:2286][web:2293][web:2296]

### 自己要客製什麼

- 研究任務流程：收問題 → 搜資料 → 摘要 → 比對 → 生成報告。
- coding 流程：讀錯誤 → 修改 → 測試 → 比較 → 選最佳 patch。
- judge 規則：以「能跑、修好、風險最小」為主，而非回答最漂亮。
- 任務類型切換：分析型、資料型、開發型分開定義。

### 可以直接用現成什麼

- 多 agent loop。
- 狀態機 / DAG 流程框架。
- 工具呼叫機制。
- 任務觀察與 tracing。

---

## C. RAG / 記憶 / 檢索層

### 建議：**檢索引擎用現成，資料結構自己定義**

研究型 AI 要真正好用，不能只靠聊天上下文，必須要有自己的知識底座。混合檢索（BM25 + 向量）是目前被反覆提到的較成熟路線，比只做向量搜尋更接近 production 級 RAG。[web:2299][web:2295]

### 可以用現成什麼

- RAGFlow / R2R / AnythingLLM 這類 ingestion 與檢索管線。[web:2295][web:2298]
- 向量資料庫。
- BM25 / keyword search。
- Embedding pipeline。

### 自己要客製什麼

- 文件分層：法條、專案文件、log、程式碼、研究筆記。
- chunk 規則：不同資料類型用不同 chunk 策略。
- metadata 欄位設計。
- Obsidian 筆記結構與雙向連結。
- 哪些內容可以進 RAG、哪些只能留本地私密層。[cite:2225][cite:2226]

---

## D. 工具執行層

### 建議：**這層一定要自己客製，是核心競爭力**

這一層就是你的 AI 到底能不能真的做事的關鍵。一般框架會有 shell、python、browser 之類的標準工具，但到了 Windows、自動修錯、PowerShell、GUI 操作、你自己的測試腳本，這裡就一定要自己定義。[cite:2274][cite:2273]

### 現成可用

- shell / terminal tool。
- Python execution。
- Git 操作。
- Docker command。
- 瀏覽器工具。

### 一定要自己客製

- PowerShell wrapper。
- Windows GUI automation。
- 測試腳本執行策略。
- 失敗重試與 rollback。
- 安全白名單／黑名單。
- 特定 repo 的 build / run / test 命令集。

---

## E. 本地模型推理層

### 建議：**伺服器用現成，模型分工自己定**

模型伺服器不值得自己重做，Ollama、vLLM、LM Studio backend 都屬於成熟底座；但你的模型角色配置需要自己決定，因為這會直接影響成本、速度與品質。[web:2272][web:2267]

### 可直接用現成什麼

- Ollama：最容易上手。[web:2151]
- vLLM：偏高效服務化部署。[web:2272]
- LM Studio backend：偏 GUI 友善。[web:2270]

### 自己要客製什麼

- 模型角色：
  - Gemma2:9b = 推理大腦。
  - DeepSeek-Coder = Worker A。
  - Qwen2.5-Coder:7b = Worker B。
- 哪些任務只用一顆模型，哪些任務要雙工人比較。
- 模型 fallback 規則。

---

## F. 基礎設施層

### 建議：**系統底座用現成，但運維規則自己訂**

Windows、WSL、Docker、venv、uv 這些都應該直接採用成熟方案，不要自己創造另一套包裝。[cite:2278]

### 自己要客製什麼

- 專案資料夾慣例。
- sandbox / production 的邊界。
- 備份策略。
- 排程執行規範。
- log retention 規則。
- 錯誤通知方式。

---

## 哪些層一定不要自己重造

- 模型下載與基本 serving。
- 基本聊天 UI。
- 通用 agent loop。
- 標準 RAG ingestion pipeline。
- Docker / Python 環境管理本身。

這些地方自己重造，通常只會增加疲勞，不會形成真正優勢。[web:2302][web:2306]

---

## 哪些層一定要自己掌握

- Windows 工具執行橋。
- 研究任務模板與決策流程。
- 測試與驗證規則。
- 私有知識結構。
- 長期記憶的筆記 schema。

真正能讓你的系統變成「你的研究型 AI」的，是這幾層，而不是底層聊天框。[cite:2274][cite:2225]

---

## 最大版本的推薦落地方案

```text
互動層：OpenHands 或 Open WebUI
Agent 層：LangGraph / OpenHands workflow
RAG 層：RAGFlow 或 R2R + Obsidian 作記憶層
工具層：自製 Windows / PowerShell / test wrapper
模型層：Ollama（Gemma2:9b + DeepSeek-Coder + Qwen2.5-Coder:7b）
基礎設施：Windows + Docker + Python venv / uv
```

這個版本不是最簡單，但它是「最大、可長期演進、仍保有現實可行性」的架構圖：底層大量沿用現成工具，上層只在真正需要競爭力與客製化的地方出手。[web:2286][web:2295][web:2151][cite:2277]

---

## 最後的設計原則

1. **先選底座，再做客製，不要反過來。**
2. **用現成的地方越多，真正需要自己維護的地方越清楚。**
3. **把客製化集中在工具層、工作流層、記憶層。**
4. **不要追求全能通用 agent，要追求你的任務場景成功率。**
5. **先做能跑的 v1，再把 Obsidian、比較器、多工模型慢慢接上去。**

