# Obsidian → RAGFlow 自動同步流程圖

## 一、整體架構總覽

```mermaid
graph TB
  subgraph "📝 Obsidian Vault (本機)"
    OB_Vault["Obsidian 法律筆記庫\n(Markdown 檔案)"]
    OB_New["新增 .md"]
    OB_Edit["修改 .md"]
    OB_Del["刪除 .md"]
    OB_Vault --> OB_New
    OB_Vault --> OB_Edit
    OB_Vault --> OB_Del
  end

  subgraph "👁️ 檔案監控層 (File Watcher)"
    FW["chokidar 即時監控\n(add / change / unlink)"]
    HASH["SHA-256 雜湊比對\n(增量同步)"]
    QUEUE["同步佇列\n(防抖 debounce 2s)"]
  end

  subgraph "⚙️ 處理層 (Sync Engine)"
    PARSE["Markdown 解析器\n- frontmatter 提取\n- 標題/標籤/連結"]
    CHUNK["智慧分段器\n- 依 ## 標題切分\n- 保留法律條號完整性"]
    META["元資料建構\n- 科目分類 (民法/刑法...)\n- 來源筆記路徑\n- 最後修改時間"]
    DEDUP["去重檢查\n- hash → RAGFlow doc_id 映射\n- 避免重複上傳"]
  end

  subgraph "☁️ RAGFlow API 層"
    RF_KB["RAGFlow 知識庫\n(Knowledge Base)"]
    RF_UP["上傳文件 API\n POST /api/v1/datasets/{id}/documents"]
    RF_DEL["刪除文件 API\n DELETE /api/v1/datasets/{id}/documents"]
    RF_PARSE["觸發解析 API\n POST /api/v1/datasets/{id}/chunks"]
    RF_LIST["查詢文件 API\n GET /api/v1/datasets/{id}/documents"]
  end

  subgraph "💾 同步狀態 DB"
    SYNC_DB["sync_state.json\n- file_path → doc_id\n- file_path → sha256\n- last_synced_at"]
  end

  OB_New --> FW
  OB_Edit --> FW
  OB_Del --> FW

  FW --> HASH
  HASH -->|"hash 變化"| QUEUE
  HASH -->|"hash 相同"| SKIP["⏭️ 跳過"]
  QUEUE --> PARSE
  PARSE --> CHUNK
  CHUNK --> META
  META --> DEDUP

  DEDUP -->|"新文件"| RF_UP
  DEDUP -->|"已存在但有變更"| RF_DEL
  RF_DEL -->|"重新上傳"| RF_UP
  DEDUP -->|"Obsidian 刪除"| RF_DEL

  RF_UP --> RF_PARSE
  RF_PARSE --> RF_KB

  DEDUP <--> SYNC_DB
  RF_UP --> SYNC_DB
  RF_DEL --> SYNC_DB
```

---

## 二、詳細同步事件流

```mermaid
sequenceDiagram
  participant OB as 📝 Obsidian
  participant FW as 👁️ File Watcher
  participant SE as ⚙️ Sync Engine
  participant DB as 💾 sync_state.json
  participant RF as ☁️ RAGFlow API

  Note over OB,RF: 🟢 情境 A：新增筆記

  OB->>FW: 儲存 民法/物權/抵押權.md
  FW->>SE: event: add, path: 民法/物權/抵押權.md
  SE->>SE: 計算 SHA-256 hash
  SE->>DB: 查詢 hash 是否存在?
  DB-->>SE: ❌ 不存在
  SE->>SE: 解析 frontmatter + 切分段落
  SE->>RF: POST /datasets/{kb_id}/documents<br/>(上傳 .md 檔)
  RF-->>SE: { doc_id: "abc123" }
  SE->>RF: POST /datasets/{kb_id}/chunks<br/>(觸發解析/向量化)
  RF-->>SE: ✅ 解析中
  SE->>DB: 寫入 { path, doc_id, hash, timestamp }

  Note over OB,RF: 🟡 情境 B：修改筆記

  OB->>FW: 修改並儲存 民法/物權/抵押權.md
  FW->>SE: event: change, path: 民法/物權/抵押權.md
  SE->>SE: 計算新 SHA-256 hash
  SE->>DB: 比對 hash
  DB-->>SE: ⚠️ hash 不同 (doc_id: abc123)
  SE->>RF: DELETE /datasets/{kb_id}/documents<br/>{ ids: ["abc123"] }
  RF-->>SE: ✅ 已刪除
  SE->>RF: POST /datasets/{kb_id}/documents<br/>(重新上傳)
  RF-->>SE: { doc_id: "def456" }
  SE->>RF: POST /datasets/{kb_id}/chunks
  SE->>DB: 更新 { path, doc_id: def456, new_hash }

  Note over OB,RF: 🔴 情境 C：刪除筆記

  OB->>FW: 刪除 民法/物權/抵押權.md
  FW->>SE: event: unlink, path: 民法/物權/抵押權.md
  SE->>DB: 查詢 doc_id
  DB-->>SE: doc_id: "def456"
  SE->>RF: DELETE /datasets/{kb_id}/documents<br/>{ ids: ["def456"] }
  RF-->>SE: ✅ 已刪除
  SE->>DB: 移除該筆記錄
```

---

## 三、Obsidian Vault 結構對應 RAGFlow 知識庫

```mermaid
graph LR
  subgraph "📂 Obsidian Vault 目錄結構"
    ROOT["法律筆記庫/"]
    CIV["民法/"]
    CRIM["刑法/"]
    ADMIN["行政法/"]
    PROC["訴訟法/"]
    ROOT --> CIV
    ROOT --> CRIM
    ROOT --> ADMIN
    ROOT --> PROC
    CIV --> CIV1["債編/"]
    CIV --> CIV2["物權/"]
    CIV --> CIV3["親屬繼承/"]
  end

  subgraph "☁️ RAGFlow 知識庫對應"
    RF_ROOT["LexMind 法律知識庫"]
    RF_TAG1["tag: 民法-債編"]
    RF_TAG2["tag: 民法-物權"]
    RF_TAG3["tag: 刑法"]
    RF_TAG4["tag: 行政法"]
    RF_ROOT --> RF_TAG1
    RF_ROOT --> RF_TAG2
    RF_ROOT --> RF_TAG3
    RF_ROOT --> RF_TAG4
  end

  CIV1 -.->|"自動同步 + 標籤"| RF_TAG1
  CIV2 -.->|"自動同步 + 標籤"| RF_TAG2
  CRIM -.->|"自動同步 + 標籤"| RF_TAG3
  ADMIN -.->|"自動同步 + 標籤"| RF_TAG4
```

---

## 四、元資料映射規則

| Obsidian 來源 | RAGFlow 目標欄位 | 範例 |
|--------------|-----------------|------|
| 檔案路徑第 1 層資料夾 | `tag` (科目) | `民法/債編/保證.md` → tag: `民法-債編` |
| frontmatter `tags:` | `tag` (附加標籤) | `tags: [物權, 抵押權]` → tags 追加 |
| frontmatter `source:` | `metadata.source` | `source: 王澤鑑教授講義` |
| `# 標題` | `document.name` | `# 抵押權的效力` → 文件名 |
| 檔案修改時間 | `metadata.updated_at` | `2026-06-29T22:00:00` |
| `[[雙向連結]]` | `metadata.related_docs` | `[[物權法通則]]` → 關聯文件 |

---

## 五、實作計畫大綱

> [!IMPORTANT]
> 需要確認以下事項才能開始實作：

### 5.1 需確認的設定

| 項目 | 問題 |
|------|------|
| **Obsidian Vault 路徑** | 您的法律筆記庫放在哪個路徑？(例如 `D:/Obsidian/法律筆記`) |
| **RAGFlow 部署方式** | RAGFlow 是本機 Docker 部署還是雲端？API 地址是？ |
| **RAGFlow API Key** | 是否已有 API Key？ |
| **知識庫 ID** | 是否已在 RAGFlow 建立好知識庫？或需要自動建立？ |
| **同步頻率** | 即時監控 (chokidar) 或定時掃描 (cron)？ |
| **整合位置** | 嵌入到 LexMind server.ts 中？還是獨立服務？ |

### 5.2 預估實作項目

| 模組 | 檔案 | 說明 |
|------|------|------|
| 檔案監控器 | `src/utils/obsidianWatcher.ts` | chokidar 監控 + debounce |
| 同步引擎 | `src/utils/ragflowSync.ts` | 解析 → hash → 上傳 → 狀態管理 |
| RAGFlow 客戶端 | `src/utils/ragflowClient.ts` | API 封裝 (上傳/刪除/查詢/解析) |
| 同步狀態 DB | `data/obsidian_sync_state.json` | 檔案 → doc_id 映射 |
| API 端點 | `server.ts` 新增 3 個端點 | 手動觸發/狀態查詢/設定管理 |
| 前端面板 | `App.tsx` 新增同步面板 | 同步狀態、日誌、手動觸發按鈕 |
LexMind-Omni-法律實務-AI-工作站/
├── server.ts                          ← 🔴 主後端 Express 伺服器 (2460 行, 123KB)
├── src/
│   ├── App.tsx                        ← 🔵 主前端 React UI (309KB)
│   └── utils/
│       ├── gpuOrchestrator.ts         ← 🟢 GPU 雙卡排程器 (288 行)
│       └── legalProofer.ts            ← 🟡 法律術語 ASR 糾錯規則引擎 (126 行)
├── extracted_sources/
│   ├── app.py                         ← ⚪ 原始 Gradio 前端 (Legacy)
│   ├── legal_glossary.json            ← 📘 法律詞彙表
│   └── scripts/                       ← 🟣 Python Agent 腳本群
│       ├── process_multimodal_file.py
│       ├── agent_core_pro.py
│       ├── auto_ingest_bot.py
│       ├── backup_manager.py
│       ├── exam_trainer.py
│       ├── ingest_law_pro.py
│       ├── law_digester.py
│       ├── law_scraper_cli.py
│       ├── legal_calendar.py
│       └── multimodal_input.py
├── scripts/                           ← 🟣 頂層獨立 Python 腳本
│   ├── auto_ingest_bot.py
│   ├── law_scraper_cli.py
│   └── visual_analyzer.py
├── .agents/skills/                    ← 🧩 12 個 Agent Skill 定義
├── data/
│   ├── database.json                  ← 💾 主資料庫 (法律智庫)
│   ├── history.json                   ← 💾 對話歷史
│   ├── cases_data.json                ← 💾 案件資料
│   └── ingest_errors.log              ← 📝 錯誤日誌
└── .env                               ← ⚙️ 環境變數配置