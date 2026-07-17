	 	  
	 	

**LexMind-Omni 旗艦技術文件 v3.1**

**完整 AI Agent Workflow 架構 × 程式碼結構 × 規範標準 × 部署架構**

***版本**：v3.1（含 Agent/Skills 程式碼與 Qdrant/長影音切片對齊完整版）*  
 ***建立日期**：2026-07-05*  
 ***本地路徑**：C:\\Users\\temp\\antigravity\\LexMind-Omni-法律實務\\-AI-工作站*  
 ***涵蓋範疇**：9 個 AI Agent 完整規格、48 個 Skills 程式碼對應、Workflow 細節規範、CODEX/CLAUDE/AGENT.md 標準、本地部署架構*

**目錄**

1. 	  
    	LexMind-Omni 	完整 AI 	Agent Workflow 架構圖  
2. 	  
    	整個系統最終程式碼結構（專案目錄樹）  
3. 	  
    	九大 	Agent 	完整規格與程式碼對應  
4. 	  
    	四十八個 	Skills 	完整清單與程式碼對應
5. 	  
    	完整 	CODEX / 	CLAUDE.md / AGENT.md 通用標準  
6. 	  
    	本地 	AI 	法律工作站完整部署架構圖  
7. 	  
    	Workflow 	細節規範：五大核心流程  
8. 	  
    	法律 	SLA 標準與效能基準

**一、LexMind-Omni 完整 AI Agent Workflow 架構圖**

LexMind-Omni 採用 **Orchestrator-Workers \+ Evaluator-Optimizer** 雙重模式，整合 Anthropic 定義的五大 Workflow 設計模式 [1](https://www.anthropic.com/research/building-effective-agents) 與 Google ADK 八大多代理設計模式 [2](https://cloud.google.com/architecture/choose-design-pattern-agentic-ai-system)，形成專為臺灣法律實務設計的七層縱深架構。

**1.1 七層架構說明**

系統由七個層次組成，各層職責嚴格分離，任何跨層呼叫均須通過標準化的 AgentMessage 協議。

**Layer 0（使用者接入層）** 支援三種接入方式：瀏覽器（localhost:3000，React \+ Vite SPA）、Streamlit UI（localhost:8501，app.py）、以及 CLI/API 客戶端（Python SDK / REST）。

**Layer 1（API 閘道層）** 由 Node.js/Express（server.ts，Port 3000）與 FastAPI（src/api/main.py，Port 8080）雙閘道組成。Express 負責前端靜態資源服務與 execFile Unicode 橋接（解決 Windows 中文路徑問題）；FastAPI 負責 OpenAPI 3.1 規格的 REST 端點。兩者均整合 JWT/API Key 驗證與 Redis Token Bucket 限流。

**Layer 2（協調器層）** 以 LocalLegalAgent（scripts/agent\_core\_pro.py）為核心，實作 LangGraph DAG 協調邏輯。Intent Classifier 依查詢類型路由至對應 Agent，RWS 動態權重系統（憲法\=1、法律\=2、命令\=3、規則\=4）在路由前自動計算法律位階加權。

**Layer 3（九大 Agent 層）** 是系統的業務邏輯核心，詳見第三章。

**Layer 4（Legal Eval Gates 層）** 七維度品質閘門，Hard Gates 任一失敗即阻斷輸出，Soft Gates 加權平均須達 0.88 以上，詳見第八章。

**Layer 5（AI 推理層）** 雙 GPU 精確分流：GPU-0 專職 Ollama 推理（DeepSeek-R1:7b），GPU-1 專職 ChromaDB 向量檢索、Whisper STT 語音轉錄、Embedding 模型。

**Layer 6（資料持久層）** 包含 ChromaDB（本地向量庫）、Qdrant 雙向量檢索庫（Dense + Sparse 混合索引）、PostgreSQL + pgvector（結構化資料）、Redis（快取 + Celery Broker）、Obsidian 知識儲存（RAGFlow 同步）、本地 JSON 儲存（database.json、cases_data.json、ingested_history.json）。

**1.2 請求處理完整時序**

sequenceDiagram

participant U as 使用者

participant GW as API Gateway

participant OA as Orchestrator (LocalLegalAgent)

participant RA as RAG 諮詢 Agent (⑧)

participant CV as 糾錯排版 Agent (①)

participant EG as Eval Gates

participant DB as ChromaDB (GPU-1)

U-\>\>GW: POST /api/v1/legal/query

GW-\>\>GW: JWT 驗證 \+ RWS 時效關鍵字偵測

GW-\>\>OA: 轉發（含 correlation\_id）

OA-\>\>OA: Intent Classification \+ RWS 加權

OA-\>\>RA: 分派法律諮詢任務

RA-\>\>DB: Hybrid Search（Dense \+ BM25 \+ RRF）

DB--\>\>RA: Top-10 相關條文（NDCG@5 ≥ 0.80）

RA-\>\>OA: 法律研究結果

OA-\>\>CV: 引用格式校驗

CV-\>\>EG: 送交七維度評測

EG-\>\>EG: Hard Gates（引用/幻覺/時效/延遲/冪等）

EG-\>\>EG: Soft Gates（格式/相關性）加權

alt Composite ≥ 0.88

EG--\>\>U: 回應 \+ 法源引用 \+ 信心分數

else BLOCK

EG--\>\>OA: 觸發重試/降級

end

**二、整個系統最終程式碼結構（專案目錄樹）**

以下為 LexMind-Omni 的完整專案目錄結構，採用\*\*領域驅動設計（DDD）\*\*分層架構，每個檔案均標注其對應的 Agent 或 Skill 歸屬。

C:\\Users\\temp\\antigravity\\LexMind-Omni-法律實務-AI-工作站\\

│

├── config.json \# SSOT 硬體配置（GPU分流/執行緒/截斷長度）

├── config\_loader.py \# apply\_hardware\_config() 動態載入

├── CLAUDE.md \# 硬體防禦紅線協議

├── CONTEXT.md \# 臺灣法律知識庫 \+ 黃少奎案特徵

├── AGENT.md \# Agent 行為規範

├── CODEX.md \# 程式碼規範

│

├── app.py \# Streamlit 主介面（Port 8501）

│ \# → Agent ⑧ RAG 諮詢 Agent 入口

│ \# → @st.cache\_resource 單例保護

│

├── server.ts # Node.js/Express API 閘道（Port 3000）

│ # → execFile Unicode 橋接

│ # → 靜態資源 charset=utf-8

│

├── data/

│   └── obsidian_sync_config.json # Obsidian API 鑰與庫同步設定

│

├── src/

│ ├── App.tsx # React 前端主應用（5個 Tab）

│ ├── components/

│ │ ├── LegalQueryTab.tsx # RAG 諮詢介面

│ │ ├── IngestTab.tsx # 教材餵食介面

│ │ ├── CaseManagementTab.tsx # 個案管理介面

│ │ ├── ExamTab.tsx # 考試培訓介面

│ │ └── AdminTab.tsx # 系統監控 + /workflows 面板

│ ├── api/

│ │ ├── main.py # FastAPI 應用程式入口（Port 8080）

│ │ ├── middleware.py # Auth + Rate Limit + CORS

│ │ └── routers/

│ │     ├── legal_query.py # POST /api/v1/legal/query

│ │     ├── documents.py # POST /api/v1/documents/upload

│ │     ├── briefs.py # POST /api/v1/briefs/generate

│ │     ├── citations.py # POST /api/v1/citations/verify

│ │     ├── cases.py # GET/POST /api/cases

│ │     └── health.py # GET /health, GET /metrics

│ ├── legal_rag/ # Qdrant 雙向量 RAG 檢索模組

│ │ ├── config.yaml # RAG 參數設定

│ │ ├── schema.py # 資料格式 Schema

│ │ ├── upsert_qdrant.py # 初始化 Qdrant 索引空間

│ │ ├── build_dense_vectors.py # Gemini 稠密向量提取

│ │ ├── build_sparse_vectors.py # BM25 稀疏向量提取

│ │ ├── ingest_documents.py # 自動化分段向量化寫入

│ │ ├── rerank.py # Gemini & Ollama 重排序

│ │ └── hybrid_search.py # 雙向量檢索核心

│ ├── long_media_pipeline/ # 長影音切片與轉錄管線

│ │ ├── config.yaml # 影音切片與 Whisper 參數設定

│ │ ├── file_watcher.py # 目錄監聽器

│ │ ├── preprocess_media.py # 影音格式前處理

│ │ ├── chunk_planner.py # 影音分片排程器

│ │ ├── stt_runner.py # Whisper ASR 轉譯

│ │ ├── merge_transcript.py # 轉譯文本合併糾錯

│ │ └── markdown_formatter.py # 格式化寫入 A:\processed_md

│ └── utils/ # 共享工具

│

├── .agents/
│   └── skills/
│       ├── 1_01_xlsx_skills/
│       ├── 1_02_docx_skills/
│       ├── 1_03_pptx_skills/
│       ├── 1_04_pdf_skills/
│       ├── 1_05_frontend_design_skills/
│       ├── 1_06_file_reading_skills/
│       ├── 1_07_pdf_reading_skills/
│       ├── 1_08_product_self_knowledge_skills/
│       ├── 2_01_skill_creator_skills/
│       ├── ...
│       └── 2_22_return_refund_skills/
│

├── scripts/

│ ├── agent_core_pro.py # LocalLegalAgent 核心

│ │ # → Agent ①③④⑦⑧⑨ 實作

│ │ # → get_chroma_client() 雙重單例

│ │ # → rag_query() 主查詢函式

│ │ # → manage_case() 案件管理

│ │ # → calculate_limitation() 時效計算

│ │ # → format_legal_doc() 書狀排版

│ │

│ ├── auto_ingest_bot.py # 全自動教材吸收機器人

│ │ # → Agent ②⑥ 實作

│ │ # → scan_local_media() 磁碟掃描

│ │ # → ingest_to_chroma() 向量入庫

│ │ # → SHA-256 去重（ingested_history.json）

│ │

│ ├── web_scraper.py # 法律網頁爬蟲

│ │ # → Agent ③ 實作

│ │ # → scrape_legal_url() 主函式

│ │

│ ├── exam_agent.py # 司法考試培訓 Agent

│ │ # → Agent ⑤ 實作

│ │     # → generate_exam() 出題

│ │     # → grade_answer() 批改

│ ├── reindex_all.py # 連動圖譜與 Obsidian 重索引

│ └── obsidian_ragflow_sync.py # Obsidian 筆記 RAGFlow 自動同步

│

├── eval/

│ ├── eval\_gates.py \# Legal Eval Gates 主框架

│ │ \# → EvalGateRunner 類別

│ │ \# → run\_all\_gates() 主評測

│ ├── citation\_hallucination.py \# Hard Gate ①② 評測器

│ ├── statute\_format\_retrieval.py \# Hard Gate ③ \+ Soft Gate ①② 評測器

│ ├── latency\_idempotency.py \# Hard Gate ④⑤ 評測器

│ ├── run\_eval\_gates.py \# CI/CD 評測執行入口

│ ├── report\_generator.py \# HTML 報告生成

│ ├── notifier.py \# Slack/Email 通知

│ ├── deploy\_guard.py \# 金絲雀部署防護

│ └── config/

│ └── ci\_config.yaml \# CI 評測配置

│

├── tests/

│ ├── golden\_dataset.jsonl \# 黃金資料集（4類法律場景）

│ ├── test\_eval\_gates.py \# 46 個評測閘門測試案例

│ ├── test\_dedup.py \# 冪等性去重測試

│ ├── test\_streamlit\_bot.py \# WebSocket 穩定性體檢

│ └── unit/

│ ├── test\_citation.py

│ ├── test\_limitation.py

│ └── test\_hybrid\_search.py

│

├── src/vector/ \# 向量索引優化層

│ ├── legal\_chunker.py \# LegalDocumentChunker

│ ├── vector\_index\_manager.py \# pgvector \+ Qdrant 管理

│ ├── hybrid\_search.py \# Dense \+ BM25 \+ RRF

│ ├── index\_benchmark.py \# FAISS 效能基準測試

│ └── local\_deployment\_config.py \# 硬體感知部署建議

│

├── src/legal\_kb/ \# 法律知識庫

│ ├── taiwan\_statutes.py \# 臺灣法典索引

│ ├── limitation\_periods.py \# 消滅時效/除斥期間知識庫

│ └── legal\_terms.py \# 法律術語詞典（BM25用）

│

├── deploy/

│ ├── docker-compose.yml \# 完整部署

│ ├── docker-compose.dev.yml \# 開發環境

│ └── nginx/nginx.conf \# 反向代理

│

├── .github/workflows/

│ ├── legal\_eval\_ci.yml \# CI/CD 主流程（5 Stages）

│ └── eval\_gates\_nightly.yml \# 夜間回歸評測

│

├── database.json \# Express 應用資料庫

├── cases\_data.json \# 訴訟個案資料

├── ingested\_history.json \# SHA-256 去重歷史

├── chosen\_paths\_buffer.json \# 待處理路徑快取

├── Makefile \# 統一命令介面

├── pyproject.toml \# Python 依賴（uv）

├── package.json \# Node.js 依賴（256套件）

├── vite.config.ts \# Vite 設定（HMR Port 24678）

└── 全自動吸收教材.bat \# Windows 一鍵啟動

**三、九大 Agent 完整規格與程式碼對應**

LexMind-Omni 共有 **9 個協作 Agent**，分為 5 個獨立專一任務 Agent 與 4 個跨模組協同 Agent。每個 Agent 均標注完整的程式碼位置、類別名稱、核心函式與對應的 API 端點，方便直接定位與管理 [3](https://github.com/harvey-ai/harvey-agents)。

**3.1 Agent 總覽矩陣**

| 				\# 			 | 				Agent 				名稱 			 | 				類型 			 | 				主程式檔案 			 | 				類別名稱 			 | 				核心函式 			 | 				API 				端點 			 |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| 				① 			 | 				糾錯排版 Agent 			 | 				獨立 			 | 				scripts/agent\_core\_pro.py 			 | 				LegalProofer 			 | 				format\_legal\_doc() 			 | 				POST 				/api/v1/briefs/format 			 |
| 				② 			 | 				磁碟掃描 Agent 			 | 				獨立 			 | 				scripts/auto\_ingest\_bot.py 			 | 				LocalMediaScanner 			 | 				scan\_local\_media() 			 | 				GET 				/api/scan-local-media 			 |
| 				③ 			 | 				網頁爬蟲 Agent 			 | 				獨立 			 | 				scripts/web\_scraper.py 			 | 				LegalWebScraper 			 | 				scrape\_legal\_url() 			 | 				POST 				/api/trigger-scraper 			 |
| 				④ 			 | 				期限審查 Agent 			 | 				獨立 			 | 				scripts/agent\_core\_pro.py 			 | 				DeadlineCalendar 			 | 				calculate\_limitation() 			 | 				POST 				/api/v1/timeline/calculate 			 |
| 				⑤ 			 | 				考試培訓 Agent 			 | 				獨立 			 | 				scripts/exam\_agent.py 			 | 				MockExamTrainer 			 | 				generate\_exam() 			 | 				POST 				/api/v1/exam/generate 			 |
| 				⑥ 			 | 				知識庫索引 Agent 			 | 				協同 			 | 				scripts/auto\_ingest\_bot.py 			 | 				KnowledgeSynthesizer 			 | 				ingest\_to\_chroma() 			 | 				POST 				/api/parse-local-file 			 |
| 				⑦ 			 | 				案件主控 Agent 			 | 				協同 			 | 				scripts/agent\_core\_pro.py 			 | 				CaseOrchestrator 			 | 				manage\_case() 			 | 				GET/POST 				/api/cases 			 |
| 				⑧ 			 | 				RAG 				諮詢 				Agent 			 | 				協同 			 | 				app.py 				\+ scripts/agent\_core\_pro.py 			 | 				RAGLegalConsult 			 | 				rag\_query() 			 | 				POST 				/api/v1/legal/query 			 |
| 				⑨ 			 | 				書狀生成 Agent 			 | 				協同 			 | 				scripts/agent\_core\_pro.py 			 | 				PleadingsDrafter 			 | 				draft\_pleading() 			 | 				POST 				/api/v1/briefs/generate 			 |

**3.2 獨立專一任務 Agent 詳細規格**

**Agent ① — 法律公文糾錯與書狀排版 Agent**

**定位**：系統的文書品質守門員，所有對外輸出的法律文書必須經此 Agent 校驗。

**程式碼位置**：

scripts/agent\_core\_pro.py

└── class LegalProofer

├── format\_legal\_doc(draft: str) \-\> FormattedDoc

├── check\_citation\_format(text: str) \-\> CitationReport

├── correct\_typos(text: str) \-\> str

└── validate\_court\_style(doc: FormattedDoc) \-\> bool

**核心 Workflow**：

flowchart LR

A\[書狀草稿輸入\] \--\> B\[Ollama 錯字校正\\nDeepSeek-R1:7b\]

B \--\> C\[法條引用格式驗證\\n正規表達式\]

C \--\> D\[縮排與排版美化\\n司法公文規範\]

D \--\> E\[Eval Gate ①\\n引用準確性≥0.95\]

E \--\>|通過| F\[輸出標準書狀\]

E \--\>|失敗| G\[標記UNVERIFIED\\n退回修正\]

**輸入/輸出規格**：

| 				項目 			 | 				規格 			 |
| :---- | :---- |
| 				輸入 			 | 				未排版法律草稿（str，最大 				150,000 				字元） 			 |
| 				輸出 			 | 				FormattedDoc（含 				content、citation\_list、format\_score） 			 |
| 				依賴服務 			 | 				Ollama 				GPU-0（錯字校正）、src/legal\_kb/taiwan\_statutes.py（條號驗證） 			 |
| 				觸發條件 			 | 				Agent 				⑨ 書狀生成完成後自動呼叫；使用者手動上傳草稿 			 |
| 				SLA 			 | 				P95 				延遲 				\< 				3000ms；格式合規分數 				≥ 0.85 			 |

**關鍵程式碼片段**：

\# scripts/agent\_core\_pro.py

class LegalProofer:

def \_\_init\_\_(self, config: dict):

self.ollama\_host \= config\["ollama\_host"\]

self.model \= config\["ollama\_model"\]

self.\_citation\_pattern \= re.compile(

r'(\[\\u4e00-\\u9fff\]{2,20}(?:法|條例|規則|辦法))第\\s\*(\\d\+(?:\-\\d\+)?)\\s\*條'

)

def format\_legal\_doc(self, draft: str) \-\> FormattedDoc:

\# Step 1: Ollama 錯字校正

corrected \= self.\_correct\_via\_ollama(draft)

\# Step 2: 法條引用格式驗證

citations \= self.\_extract\_and\_verify\_citations(corrected)

\# Step 3: 排版美化

formatted \= self.\_apply\_court\_style(corrected)

return FormattedDoc(

content\=formatted,

citation\_list\=citations,

format\_score\=self.\_score\_format(formatted)

)

**Agent ② — 本地磁碟教材登記 Agent**

**定位**：系統的資料採集入口，負責遍歷本機所有磁碟（A-Z）搜尋法律教材。

**程式碼位置**：

scripts/auto\_ingest\_bot.py

└── class LocalMediaScanner

├── scan\_local\_media(path: str, max\_depth: int \= 4\) \-\> list\[FileMetadata\]

├── scan\_all\_drives() \-\> list\[FileMetadata\] \# 遍歷 A-Z 磁碟

├── filter\_legal\_folders(paths: list) \-\> list \# 法律關鍵字篩選

├── estimate\_processing\_time(files: list) \-\> ETAReport

├── pause\_ingestion() / resume\_ingestion() / abort\_ingestion()

└── write\_to\_buffer(paths: list) \-\> None \# → chosen\_paths\_buffer.json

**核心 Workflow**：

flowchart TD

A\[啟動掃描\\n全自動吸收教材.bat\] \--\> B\[遍歷 A-Z 磁碟\\n過濾系統資料夾\]

B \--\> C{法律關鍵字匹配?\\n法律/法規/法庭/訴訟\\n民法/刑法/行政法}

C \--\>|否| B

C \--\>|是| D\[副檔名判斷\\nmp4/mp3/pdf/txt\]

D \--\> E\[計算 ETA\\n時間投影\]

E \--\> F\[寫入 chosen\_paths\_buffer.json\]

F \--\> G\[觸發 Agent ⑥ 知識庫索引\]

**升級後的批次控制子功能**（v2.0 新增）：

| 				子功能 			 | 				函式 			 | 				說明 			 |
| :---- | :---- | :---- |
| 				時間估算 			 | 				estimate\_processing\_time() 			 | 				分析檔案格式/大小，計算預估開始/結束時間 			 |
| 				批次控制 			 | 				pause/resume/abort\_ingestion() 			 | 				即時暫停、繼續、中止執行緒 			 |
| 				分批間隔 			 | 				set\_batch\_config(size, 				interval\_sec) 			 | 				防止硬體瞬間過載 			 |
| 				進度回報 			 | 				GET 				/api/ingest-progress 			 | 				前端即時進度條 			 |

**API 端點對應**：

GET /api/list-directories → scan\_local\_media() 目錄瀏覽

GET /api/scan-local-media → scan\_local\_media() 教材掃描

POST /api/trigger-ingest → 啟動批次吸收任務

GET /api/ingest-progress → 即時進度查詢

**Agent ③ — 法律網頁爬蟲 Agent**

**定位**：外部法律資訊的自動採集器，爬取裁判書、法規、考題等網路資源。

**程式碼位置**：

scripts/web\_scraper.py

└── class LegalWebScraper

├── scrape\_legal\_url(url: str) \-\> ScrapedContent

├── scrape\_judgment(case\_no: str) \-\> Judgment \# 裁判書查詢

├── scrape\_exam\_questions(source: str) \-\> list\[ExamQ\] \# 考題爬取

├── clean\_html\_noise(raw\_html: str) \-\> str \# 去除廣告/選單

└── ai\_extract\_content(text: str) \-\> str \# Ollama AI 清洗

**支援爬取目標**：

| 				目標 			 | 				URL 				模式 			 | 				處理方式 			 |
| :---- | :---- | :---- |
| 				司法院裁判書 			 | 				judgment.judicial.gov.tw 			 | 				HTML 				解析 				\+ 				AI 清洗 			 |
| 				全國法規資料庫 			 | 				law.moj.gov.tw 			 | 				結構化 JSON 				API 			 |
| 				考選部考題 			 | 				wwwc.moex.gov.tw 			 | 				表格解析 			 |
| 				高點/保成補習班 			 | 				自訂 CSS 				Selector 			 | 				AI 				提煉考題結構 			 |

**API 端點對應**：

POST /api/trigger-scraper → scrape\_legal\_url()

GET /api/scrape-status → 爬蟲進度查詢（scraper\_status.json）

POST /api/v1/documents/scrape → 批次 URL 爬取

**Agent ④ — 訴訟期限與日曆排程審查 Agent**

**定位**：系統的法律時效守衛，零容忍錯誤（Hard Gate 閾值 \= 1.00）。

**程式碼位置**：

scripts/agent\_core\_pro.py

└── class DeadlineCalendar

├── calculate\_limitation(cause: str, incident\_date: str,

│ discovery\_date: str) \-\> LimitationResult

├── check\_rws\_trigger(text: str) \-\> bool \# 時效關鍵字偵測

├── get\_applicable\_statute(cause: str) \-\> StatuteRef \# 適用法條查詢

└── format\_warning\_header(result: LimitationResult) \-\> str \# 紅字警示

**臺灣法律時效知識庫**（src/legal\_kb/limitation\_periods.py）：

| 				請求權類型 			 | 				時效期間 			 | 				法律依據 			 | 				起算點 			 |
| :---- | :---- | :---- | :---- |
| 				侵權行為損害賠償 			 | 				2 				年（知悉）/ 				10 年（行為） 			 | 				民法第 197 				條 			 | 				知悉日 / 				行為日 			 |
| 				一般消滅時效 			 | 				15 				年 			 | 				民法第 125 				條 			 | 				請求權可行使時 			 |
| 				短期消滅時效 			 | 				2 				年 			 | 				民法第 126-127 				條 			 | 				各款規定 			 |
| 				勞資爭議 			 | 				2 				年 			 | 				勞動基準法第 58 				條 			 | 				事由發生日 			 |
| 				刑事追訴時效（詐欺） 			 | 				10 				年 			 | 				刑法第 80 				條 			 | 				犯罪終了日 			 |
| 				刑事告訴乃論 			 | 				6 				個月 			 | 				刑事訴訟法第 237 				條 			 | 				知悉犯人日 			 |
| 				借名登記返還 			 | 				15 				年 			 | 				民法第 125 				條 			 | 				契約終止日 			 |
| 				不當得利 			 | 				15 				年 			 | 				民法第 125 				條 			 | 				利益取得日 			 |

**RWS 時效觸發規則**（CONTEXT.md 定義）：

*若對話命中「消滅時效」、「追訴權時效」、「除斥期間」、「罹於時效」等關鍵字，RWS 檢索加權強制拉滿（所有法律位階權重設為最高），並於回答首段輸出**粗體紅字時效消滅警示**。*

**API 端點對應**：

POST /api/v1/timeline/calculate → calculate\_limitation()

GET /api/v1/timeline/statutes → 時效法條清單查詢

**Agent ⑤ — 司法考試與法律培訓 Agent**

**定位**：法律知識的互動學習引擎，支援司法官考試、律師考試、法律助理培訓。

**程式碼位置**：

scripts/exam\_agent.py

└── class MockExamTrainer

├── generate\_exam(subject: str, difficulty: str) \-\> ExamPaper

├── grade\_answer(paper: ExamPaper, answer: str) \-\> GradeReport

├── explain\_wrong\_answer(question: ExamQ, answer: str) \-\> Explanation

├── ingest\_exam\_question(title: str, body: str, explanation: str) \-\> None

└── crawl\_past\_exams(source: str) \-\> list\[ExamQ\] \# 考題爬取整合

**支援考試科目**：民法、刑法、民事訴訟法、刑事訴訟法、行政法、憲法、商事法、國際私法。

**API 端點對應**：

POST /api/v1/exam/generate → generate\_exam()

POST /api/v1/exam/grade → grade\_answer()

POST /api/v1/exam/ingest → ingest\_exam\_question()

**3.3 跨模組協同 Agent 詳細規格**

**Agent ⑥ — 法律知識庫歸類與索引 Agent**

**定位**：資料處理中樞，協調 Agent ②（磁碟掃描）與 Agent ③（網頁爬蟲）的輸出，執行多模態教材吸收。

**程式碼位置**：

scripts/auto\_ingest\_bot.py

└── class KnowledgeSynthesizer

├── ingest\_to\_chroma(file\_path: str, metadata: dict) \-\> IngestResult

├── process\_audio\_video(path: str) \-\> str \# Whisper STT → GPU-1

├── process\_pdf(path: str) \-\> str \# PyPDF2 \+ OCR

├── process\_text(path: str) \-\> str \# 直接讀取截斷150K

├── correct\_transcription(text: str) \-\> str \# Ollama 錯字校正

├── upsert\_vector(text: str, metadata: dict) \-\> None \# ChromaDB upsert

└── log\_error(file: str, error: str) \-\> None \# → ingest\_errors.log

**升級後的子功能**（v2.0 新增）：

| 				子功能 			 | 				函式 			 | 				說明 			 |
| :---- | :---- | :---- |
| 				錯誤記錄器 			 | 				log\_error() 			 | 				自動寫入 				ingest\_errors.log，含出錯檔案\+時間戳 			 |
| 				吞吐限額提升 			 | 				設定 50MB 				上限 			 | 				由 100KB 				提升至 				50MB，支援巨幅法律 				PDF 			 |
| 				科目前綴命名 			 | 				apply\_subject\_prefix() 			 | 				\[科目\]\_\[章節\]\_\[原檔名\] 				自動套用 			 |
| 				OOM 				斷路器 			 | 				\_cleanup\_memory() 			 | 				gc.collect() 				\+ torch.cuda.empty\_cache() 			 |

**三路教材處理管線**：

flowchart TD

A\[教材檔案\] \--\> B{副檔名判斷}

B \--\>|mp4/mp3/wav| C\[Whisper STT\\nGPU-1\\n\~14 min/檔\]

B \--\>|pdf| D\[PyPDF2 文字提取\\n+ OCR 備援\]

B \--\>|txt| E\[直接讀取\\n截斷 150,000 字\]

C \--\> F\[Ollama 錯字校正\\nGPU-0\]

D \--\> F

E \--\> F

F \--\> G\[SHA-256 去重檢查\\ningested\_history.json\]

G \--\>|已存在| H\[跳過 Skip\]

G \--\>|新增| I\[ChromaDB upsert\\nGPU-1\]

I \--\> J\[更新去重記錄\]

**API 端點對應**：

POST /api/parse-local-file → ingest\_to\_chroma()（主吸收入口）

POST /api/v1/documents/upload → 手動上傳文件

GET /api/log-error → 錯誤日誌查詢

**Agent ⑦ — 訴訟案件與關係人主控 Agent**

**定位**：業務邏輯中樞，維護所有案件的完整上下文，是 Agent ⑧ 和 ⑨ 的資訊供應者。

**程式碼位置**：

scripts/agent\_core\_pro.py

└── class CaseOrchestrator

├── manage\_case(case\_id: str, action: str, data: dict) \-\> CaseResult

├── get\_case\_context(case\_id: str) \-\> CaseContext

├── update\_timeline(case\_id: str, event: TimelineEvent) \-\> None

├── add\_stakeholder(case\_id: str, person: Stakeholder) \-\> None

├── set\_defense\_strategy(case\_id: str, strategy: str) \-\> None

└── get\_deadline\_alerts(case\_id: str) \-\> list\[Alert\]

**資料模型**（cases\_data.json）：

// server.ts 中定義的 Case Schema

interface Case {

id: string; // UUID

title: string; // 案件名稱

case\_number: string; // 案號（如：114 他 6668）

court: string; // 法院

stakeholders: Stakeholder\[\]; // 關係人清單

timeline: TimelineEvent\[\]; // 案件時間線

defense\_strategy: string; // 攻防策略

evidence\_list: Evidence\[\]; // 證物清單

deadlines: Deadline\[\]; // 期限警示

chat\_history: ChatMessage\[\]; // 個案對話記錄

}

**API 端點對應**：

GET /api/cases → 案件列表

POST /api/cases → 新增案件

GET /api/cases/:id → 案件詳情 \+ 上下文

PUT /api/cases/:id → 更新案件

POST /api/cases/:id/stakeholders → 新增關係人

POST /api/cases/:id/timeline → 新增時間線事件

**Agent ⑧ — RAG 智能法律諮詢 Agent**

**定位**：系統的知識輸出核心，整合 Agentic RAG 多輪動態檢索，產出具法源依據的法律意見。

### 專案自建專屬子模組（更名規避版）：
1. **LexMind-Bot** (隨身法學智能助理)：代替原小貔貅/SuitAI精簡對話視窗。內嵌白話文引導Prompt，於Streamlit側邊欄渲染微型白箱答詢面板。
2. **LexMind-VJD** (判決檢索真偽驗證機制)：代替原VJP判決真偽校驗。自動提取AI回答中的最高法院案號，並回溯ChromaDB驗證，防範判決幻覺。
3. **十四法科隨身法學問答**：教材檢索頁下方的專學科控制台，自動載入14類法科專科Prompt對位答詢。

**程式碼位置**：

app.py \# Streamlit 入口（@st.cache\_resource 單例）

scripts/agent\_core\_pro.py

└── class RAGLegalConsult

├── rag\_query(question: str, case\_id: str \= None) \-\> LegalResponse

├── \_plan\_retrieval(question: str) \-\> RetrievalPlan \# Agentic RAG 規劃

├── \_execute\_retrieval(plan: RetrievalPlan) \-\> list\[Chunk\]

├── \_evaluate\_retrieval\_quality(chunks: list) \-\> QualityScore

├── \_refine\_query(plan: RetrievalPlan, feedback: str) \-\> RetrievalPlan

├── \_build\_prompt(question: str, context: list, case: CaseContext) \-\> str

└── \_generate\_response(prompt: str) \-\> LegalResponse

**Agentic RAG 多輪動態檢索流程**：

flowchart TD

A\[律師提問\] \--\> B\[RWS 時效關鍵字偵測\]

B \--\> C\[制定檢索計畫\\n\_plan\_retrieval\]

C \--\> D\[執行第一輪檢索\\nChromaDB NDCG@5\]

D \--\> E{品質評估\\n\_evaluate\_retrieval\_quality}

E \--\>|不足 QualityScore\<0.7| F\[重新措辭查詢\\n\_refine\_query\]

F \--\> D

E \--\>|充分| G\[案件背景整合\\nAgent⑦ CaseContext\]

G \--\> H\[組裝 Prompt\\n法律位階 \+ 案情 \+ 法條\]

H \--\> I\[Ollama LLM 生成\\nDeepSeek-R1:7b GPU-0\]

I \--\> J\[引用驗證\\nAgent① 格式校驗\]

J \--\> K\[Eval Gates 七維度評測\]

K \--\> L\[輸出含法源依據的法律意見\]

**混合搜尋策略**（src/vector/hybrid\_search.py）：

\# Dense \+ BM25 \+ RRF 融合

result \= hybrid\_search(

query\=normalize\_legal\_query(question),

top\_k\=10,

filters\={"jurisdiction": "taiwan"},

dense\_weight\=0.7, \# 語義搜尋

sparse\_weight\=0.3, \# BM25 關鍵字

score\_threshold\=0.5,

rrf\_k\=60, \# RRF 平滑常數

)

**API 端點對應**：

POST /api/v1/legal/query → rag\_query()（主查詢入口）

POST /api/v1/citations/verify → 引用驗證子功能

GET /api/system-status → 系統健康診斷（含 Ollama 延遲 34ms）

**Agent ⑨ — 訴訟書狀與答辯狀生成 Agent**

**定位**：文書產出終端，綜合案情與法理生成書狀初稿，並自動觸發 Agent ① 進行二次校對。

### 專案自建文書與審查子模組：
1. **LexMind-Contract** (智能契約起草)：支持買賣、房屋租賃、不動產借名登記契約書的標準化起草。
2. **LexMind-Notice** (存證信函起草助理)：支持催告給付、智財侵權警告信函生成。
3. **LexMind-Review** (書狀契約合規智慧審查)：代替原CWAI。讓律師粘貼合約條款，檢驗違約金限制、解約權死循環與管轄法院智慧診斷。

**程式碼位置**：

scripts/agent\_core\_pro.py

└── class PleadingsDrafter

├── draft\_pleading(case\_id: str, doc\_type: str,

│ claims: list\[str\]) \-\> PleadingDraft

├── generate\_complaint() \-\> str \# 起訴狀

├── generate\_defense() \-\> str \# 答辯狀

├── generate\_motion() \-\> str \# 聲請書

├── generate\_report() \-\> str \# 陳報狀

└── \_auto\_proofread(draft: str) \-\> str \# 自動呼叫 Agent①

**書狀生成 Workflow**：

flowchart LR

A\[律師指定\\n書狀類型+主張\] \--\> B\[Agent⑦\\n取得案件上下文\]

B \--\> C\[Agent⑧\\n取得法理依據\]

C \--\> D\[Ollama LLM\\n生成書狀初稿\]

D \--\> E\[Agent①\\n自動校對排版\]

E \--\> F\[Eval Gate\\n格式合規≥0.85\]

F \--\>|通過| G\[輸出最終書狀\]

F \--\>|失敗| D

**支援書狀類型**：

| 				書狀類型 			 | 				doc\_type 				參數 			 | 				說明 			 |
| :---- | :---- | :---- |
| 				起訴狀 			 | 				complaint 			 | 				民事/刑事起訴 			 |
| 				答辯狀 			 | 				defense 			 | 				被告答辯 			 |
| 				聲請書 			 | 				motion 			 | 				保全/假扣押等 			 |
| 				陳報狀 			 | 				report 			 | 				事實陳報 			 |
| 				上訴狀 			 | 				appeal 			 | 				上訴理由 			 |

**API 端點對應**：

POST /api/v1/briefs/generate → draft\_pleading()

POST /api/v1/briefs/format → 格式校驗（Agent①）

GET /api/v1/briefs/:id → 書狀查詢

**四、四十八個 Skills 完整清單與程式碼對應**

LexMind-Omni 的 Skills 體系遵循 Anthropic Claude Code 的 Skills 設計理念 [4](https://www.anthropic.com/engineering/claude-code-best-practices)：**按需載入、路徑限定、漸進揭露**。Skills 是封裝特定任務類型的打包指令，僅在任務需要時才載入，避免上下文視窗臃腫。

系統共定義 **48 個 Skills**，包含 18 個核心法律與系統 Skills，以及 30 個外部導入輔助 Skills (S19–S48)。

**4.1 Skills 總覽矩陣**

| 				\# 			 | 				Skill 				名稱 			 | 				類別 			 | 				觸發條件 			 | 				載入路徑 			 | 				對應程式碼 			 |
| :---- | :---- | :---- | :---- | :---- | :---- |
| 				S01 			 | 				legal-citation-check 			 | 				法律品質 			 | 				任何法律文本輸出前 			 | 				skills/citation/ 			 | 				eval/citation\_hallucination.py 			 |
| 				S02 			 | 				hallucination-guard 			 | 				法律品質 			 | 				LLM 				生成後 			 | 				skills/hallucination/ 			 | 				eval/citation\_hallucination.py 			 |
| 				S03 			 | 				limitation-calculator 			 | 				法律品質 			 | 				命中時效關鍵字 			 | 				skills/limitation/ 			 | 				scripts/agent\_core\_pro.py::DeadlineCalendar 			 |
| 				S04 			 | 				rws-weight-engine 			 | 				法律品質 			 | 				所有 RAG 				查詢前 			 | 				skills/rws/ 			 | 				scripts/agent\_core\_pro.py::rws\_weight() 			 |
| 				S05 			 | 				brief-formatter 			 | 				文書處理 			 | 				書狀生成後 			 | 				skills/brief/ 			 | 				scripts/agent\_core\_pro.py::LegalProofer 			 |
| 				S06 			 | 				court-style-validator 			 | 				文書處理 			 | 				書狀輸出前 			 | 				skills/court-style/ 			 | 				eval/statute\_format\_retrieval.py 			 |
| 				S07 			 | 				whisper-transcribe 			 | 				多模態 			 | 				音視頻檔案輸入 			 | 				skills/whisper/ 			 | 				scripts/auto\_ingest\_bot.py::process\_audio\_video 			 |
| 				S08 			 | 				pdf-ocr-extract 			 | 				多模態 			 | 				PDF 				檔案輸入 			 | 				skills/pdf-ocr/ 			 | 				scripts/auto\_ingest\_bot.py::process\_pdf 			 |
| 				S09 			 | 				legal-web-scrape 			 | 				資料採集 			 | 				爬蟲任務觸發 			 | 				skills/scraper/ 			 | 				scripts/web\_scraper.py::LegalWebScraper 			 |
| 				S10 			 | 				exam-question-parse 			 | 				資料採集 			 | 				考題爬取任務 			 | 				skills/exam-parse/ 			 | 				scripts/exam\_agent.py::crawl\_past\_exams 			 |
| 				S11 			 | 				hybrid-search 			 | 				向量檢索 			 | 				RAG 				查詢執行 			 | 				skills/search/ 			 | 				src/vector/hybrid\_search.py 			 |
| 				S12 			 | 				chroma-upsert 			 | 				向量檢索 			 | 				教材吸收完成 			 | 				skills/chroma/ 			 | 				scripts/auto\_ingest\_bot.py::upsert\_vector 			 |
| 				S13 			 | 				hnsw-index-tune 			 | 				向量檢索 			 | 				索引效能退化警報 			 | 				skills/hnsw/ 			 | 				src/vector/index\_benchmark.py 			 |
| 				S14 			 | 				eval-gate-runner 			 | 				CI/CD 			 | 				PR 				合併前 			 | 				skills/eval/ 			 | 				eval/run\_eval\_gates.py 			 |
| 				S15 			 | 				deploy-guard 			 | 				CI/CD 			 | 				部署前驗證 			 | 				skills/deploy/ 			 | 				eval/deploy\_guard.py 			 |
| 				S16 			 | 				oom-circuit-breaker 			 | 				系統防護 			 | 				記憶體使用率 \> 				85% 			 | 				skills/oom/ 			 | 				config\_loader.py::cleanup\_memory 			 |
| 				S17 			 | 				chroma-singleton 			 | 				系統防護 			 | 				ChromaDB 				初始化時 			 | 				skills/singleton/ 			 | 				scripts/agent\_core\_pro.py::get\_chroma\_client 			 |
| 				S18 			 | 				git-rollback-protocol 			 | 				系統防護 			 | 				連續 3 				輪除錯失敗 			 | 				skills/rollback/ 			 | 				CLAUDE.md 				協議 			 |
| S19 | xlsx-skills | 外部技能-辦公 | 需要讀寫/編輯 Excel 檔案時 | .agents/skills/1_01_xlsx_skills/ | [1_01_xlsx_skills](file:///.agents/skills/1_01_xlsx_skills/) |
| S20 | docx-skills | 外部技能-辦公 | 需要讀寫/起草 Word 檔案時 | .agents/skills/1_02_docx_skills/ | [1_02_docx_skills](file:///.agents/skills/1_02_docx_skills/) |
| S21 | pptx-skills | 外部技能-辦公 | 需要起草/解析 PowerPoint 時 | .agents/skills/1_03_pptx_skills/ | [1_03_pptx_skills](file:///.agents/skills/1_03_pptx_skills/) |
| S22 | pdf-skills | 外部技能-辦公 | 需要合併/拆分/浮水印 PDF 時 | .agents/skills/1_04_pdf_skills/ | [1_04_pdf_skills](file:///.agents/skills/1_04_pdf_skills/) |
| S23 | frontend-design | 外部技能-設計 | 需要設計高質感網頁介面時 | .agents/skills/1_05_frontend_design_skills/ | [1_05_frontend_design_skills](file:///.agents/skills/1_05_frontend_design_skills/) |
| S24 | file-reading | 外部技能-工具 | 需要安全解析未知上傳檔案時 | .agents/skills/1_06_file_reading_skills/ | [1_06_file_reading_skills](file:///.agents/skills/1_06_file_reading_skills/) |
| S25 | pdf-reading | 外部技能-工具 | 需要深度讀取/OCR PDF 檔案時 | .agents/skills/1_07_pdf_reading_skills/ | [1_07_pdf_reading_skills](file:///.agents/skills/1_07_pdf_reading_skills/) |
| S26 | product-self-knowledge | 外部技能-知識 | 需要確認 Anthropic 產品細節時 | .agents/skills/1_08_product_self_knowledge_skills/ | [1_08_product_self_knowledge_skills](file:///.agents/skills/1_08_product_self_knowledge_skills/) |
| S27 | skill-creator | 外部技能-系統 | 需要動態生成/修復 Agent 技能時 | .agents/skills/2_01_skill_creator_skills/ | [2_01_skill_creator_skills](file:///.agents/skills/2_01_skill_creator_skills/) |
| S28 | algorithmic-art | 外部技能-藝術 | 需要使用程式代碼生成藝術圖形時 | .agents/skills/2_02_algorithmic_art_skills/ | [2_02_algorithmic_art_skills](file:///.agents/skills/2_02_algorithmic_art_skills/) |
| S29 | canvas-design | 外部技能-設計 | 需要生成海報/視覺插圖時 | .agents/skills/2_03_canvas_design_skills/ | [2_03_canvas_design_skills](file:///.agents/skills/2_03_canvas_design_skills/) |
| S30 | theme-factory | 外部技能-設計 | 需要套用視覺佈景主題時 | .agents/skills/2_04_theme_factory_skills/ | [2_04_theme_factory_skills](file:///.agents/skills/2_04_theme_factory_skills/) |
| S31 | mcp-builder | 外部技能-系統 | 需要客製化建置 MCP 伺服器時 | .agents/skills/2_05_mcp_builder_skills/ | [2_05_mcp_builder_skills](file:///.agents/skills/2_05_mcp_builder_skills/) |
| S32 | slack-gif-creator | 外部技能-媒體 | 需要生成 Slack 動態 GIF 時 | .agents/skills/2_06_slack_gif_creator_skills/ | [2_06_slack_gif_creator_skills](file:///.agents/skills/2_06_slack_gif_creator_skills/) |
| S33 | web-artifacts-builder | 外部技能-設計 | 需要建立複雜多組件 Web Artifacts 時 | .agents/skills/2_07_web_artifacts_builder_skills/ | [2_07_web_artifacts_builder_skills](file:///.agents/skills/2_07_web_artifacts_builder_skills/) |
| S34 | brand-guidelines | 外部技能-設計 | 需要套用 Anthropic 品牌視覺標準時 | .agents/skills/2_08_brand_guidelines_skills/ | [2_08_brand_guidelines_skills](file:///.agents/skills/2_08_brand_guidelines_skills/) |
| S35 | doc-coauthoring | 外部技能-寫作 | 需要引導使用者進行文件共創時 | .agents/skills/2_09_doc_coauthoring_skills/ | [2_09_doc_coauthoring_skills](file:///.agents/skills/2_09_doc_coauthoring_skills/) |
| S36 | internal-comms | 外部技能-寫作 | 需要編寫內部備忘錄/報告時 | .agents/skills/2_10_internal_comms_skills/ | [2_10_internal_comms_skills](file:///.agents/skills/2_10_internal_comms_skills/) |
| S37 | event-planning | 外部技能-工具 | 需要規劃專案時程與預算時 | .agents/skills/2_11_event_planning_skills/ | [2_11_event_planning_skills](file:///.agents/skills/2_11_event_planning_skills/) |
| S38 | financial-calculator | 外部技能-工具 | 需要計算利息/稅率情境分析時 | .agents/skills/2_12_financial_calculator_skills/ | [2_12_financial_calculator_skills](file:///.agents/skills/2_12_financial_calculator_skills/) |
| S39 | benepass-reimbursement | 外部技能-工具 | 需要向 Benepass 申報福利報銷時 | .agents/skills/2_13_benepass_reimbursement_skills/ | [2_13_benepass_reimbursement_skills](file:///.agents/skills/2_13_benepass_reimbursement_skills/) |
| S40 | file-expenses | 外部技能-工具 | 需要在 Brex/Concur 進行費用報銷時 | .agents/skills/2_14_file_expenses_skills/ | [2_14_file_expenses_skills](file:///.agents/skills/2_14_file_expenses_skills/) |
| S41 | file-form | 外部技能-工具 | 需要填寫政府公文或行政表單時 | .agents/skills/2_15_file_form_skills/ | [2_15_file_form_skills](file:///.agents/skills/2_15_file_form_skills/) |
| S42 | call-to-book | 外部技能-媒體 | 需要預約行程並自動記錄日曆時 | .agents/skills/2_16_call_to_book_skills/ | [2_16_call_to_book_skills](file:///.agents/skills/2_16_call_to_book_skills/) |
| S43 | cancel-unsubscribe | 外部技能-工具 | 需要審計並取消訂閱服務時 | .agents/skills/2_17_cancel_unsubscribe_skills/ | [2_17_cancel_unsubscribe_skills](file:///.agents/skills/2_17_cancel_unsubscribe_skills/) |
| S44 | grocery-shopping | 外部技能-日常 | 需要自動採購教材辦公雜貨時 | .agents/skills/2_18_grocery_shopping_skills/ | [2_18_grocery_shopping_skills](file:///.agents/skills/2_18_grocery_shopping_skills/) |
| S45 | hire-help | 外部技能-日常 | 需要在 TaskRabbit 聘用臨時勞務時 | .agents/skills/2_19_hire_help_skills/ | [2_19_hire_help_skills](file:///.agents/skills/2_19_hire_help_skills/) |
| S46 | meal-delivery | 外部技能-日常 | 需要訂購送餐服務時 | .agents/skills/2_20_meal_delivery_skills/ | [2_20_meal_delivery_skills](file:///.agents/skills/2_20_meal_delivery_skills/) |
| S47 | prescription-refill | 外部技能-日常 | 需要處理藥品配方續開預約時 | .agents/skills/2_21_prescription_refill_skills/ | [2_21_prescription_refill_skills](file:///.agents/skills/2_21_prescription_refill_skills/) |
| S48 | return-refund | 外部技能-日常 | 需要辦理退貨與退款流程時 | .agents/skills/2_22_return_refund_skills/ | [2_22_return_refund_skills](file:///.agents/skills/2_22_return_refund_skills/) |

**4.2 Skills 詳細規格**

**法律品質類 Skills（S01–S04）**

**S01 legal-citation-check** 是最核心的法律品質 Skill，在任何法律文本輸出前自動載入。它使用正規表達式驗證臺灣法律條文引用格式（法典名稱第X條第X項），並對照 src/legal\_kb/taiwan\_statutes.py 中的法典索引確認條號存在性。對應程式碼為 eval/citation\_hallucination.py 中的 CitationAccuracyEvaluator 類別，核心函式 evaluate(response, expected\_citations) 返回 0.0–1.0 的準確率分數，Hard Gate 閾值為 0.95。

**S02 hallucination-guard** 在 LLM 生成後立即執行，偵測虛構法典名稱與條號。它維護一份已知虛構法律名稱的黑名單（如「民事保護法」、「法律保護條例」等），並對所有引用進行可溯源性驗證。對應 eval/citation\_hallucination.py 中的 HallucinationRateEvaluator，Hard Gate 閾值為幻覺率 \< 0.05。

**S03 limitation-calculator** 在對話命中時效關鍵字時自動載入，執行確定性的時效計算。它不依賴 LLM 進行時效計算（避免幻覺），而是直接查詢 src/legal\_kb/limitation\_periods.py 中的知識庫，返回精確的截止日期與剩餘天數。Hard Gate 閾值為正確率 \= 1.00（零容忍）。

**S04 rws-weight-engine** 在所有 RAG 查詢前執行，依據中華民國法律位階體系（憲法\=1、法律\=2、命令\=3、規則\=4）對檢索結果進行加權排序。當命中時效關鍵字時，強制將所有法律位階權重設為最高，確保時效相關條文優先出現在檢索結果頂部。

**多模態類 Skills（S07–S08）**

**S07 whisper-transcribe** 在音視頻檔案輸入時載入，呼叫 Whisper STT 模型（運行於 GPU-1）進行語音轉文字。最大並行任務數為 2（雙 GPU 各 1 個），單檔處理時間約 14 分鐘。轉錄完成後自動觸發 Ollama 錯字校正（GPU-0）。

**S08 pdf-ocr-extract** 在 PDF 檔案輸入時載入，優先使用 PyPDF2 提取文字，若文字提取失敗（掃描版 PDF）則啟動 OCR 備援。文字截斷上限為 150,000 字元（config.json 的 chroma\_text\_limit），確保完整保留判決書事實。

**系統防護類 Skills（S16–S18）**

**S16 oom-circuit-breaker** 在記憶體使用率超過 85% 時自動觸發，執行 gc.collect() 與 torch.cuda.empty\_cache() 釋放 GPU 記憶體。此 Skill 在 Ingestion 迴圈與 RAG 對話迴圈的每次迭代末端均會執行。

**S17 chroma-singleton** 確保 ChromaDB 在整個進程生命週期內只初始化一次 PersistentClient，防止 SQLite 鎖庫死結（database locked 錯誤）。採用雙重單例模式：模組級 \_CHROMA\_CLIENTS 字典（agent\_core\_pro.py）\+ Streamlit 層級 @st.cache\_resource（app.py）。

**S18 git-rollback-protocol** 是 CLAUDE.md 中定義的除錯紀律：若連續 3 輪除錯 Bug 未減或發生錯誤漂移，必須執行 git rollback \<safe-commit-sha\> 退回最近的安全綠色節點，重新審視底層問題，禁止繼續堆疊補丁。

**4.3 Skills 載入規則**

flowchart TD

A\[任務請求\] \--\> B{任務類型判斷}

B \--\>|法律文本輸出| C\[載入 S01 \+ S02\]

B \--\>|時效關鍵字命中| D\[載入 S03 \+ S04\]

B \--\>|音視頻輸入| E\[載入 S07\]

B \--\>|PDF 輸入| F\[載入 S08\]

B \--\>|RAG 查詢| G\[載入 S04 \+ S11 \+ S12\]

B \--\>|書狀生成| H\[載入 S05 \+ S06 \+ S01\]

B \--\>|CI/CD 觸發| I\[載入 S14 \+ S15\]

B \--\>|記憶體警報| J\[載入 S16 \+ S17\]

B \--\>|除錯失敗 3 輪| K\[載入 S18\]

**五、完整 CODEX / CLAUDE.md / AGENT.md 通用標準**

**CODEX.md — 程式碼規範與開發標準**

**C1. 工具鏈標準**

本專案以 **Python 3.12+**（後端 AI 邏輯）與 **TypeScript/Node.js 22**（前端與 API 閘道）為雙語言架構。所有程式碼合併前須通過以下工具鏈：

| 				工具 			 | 				語言 			 | 				最低標準 			 |
| :---- | :---- | :---- |
| 				ruff 			 | 				Python 			 | 				零 error，零 				warning 			 |
| 				mypy 				\--strict 			 | 				Python 			 | 				零 type 				error 			 |
| 				bandit 				\-ll 			 | 				Python 			 | 				零 high/medium 				security issue 			 |
| 				eslint 			 | 				TypeScript 			 | 				零 error 			 |
| 				tsc 				\--noEmit 			 | 				TypeScript 			 | 				零 compile 				error 			 |
| 				pytest 			 | 				Python 			 | 				覆蓋率 ≥ 85%，46 				個測試案例全通過 			 |

**C2. 命名規範**

Python 模組使用 snake\_case，法律領域模組以 legal\_ 為前綴。TypeScript 元件使用 PascalCase，API 路由使用 kebab-case（如 /api/scan-local-media）。Agent 類別以 Agent 結尾，評測器以 Evaluator 結尾，Skill 以 Skill 結尾。

**C3. 法律 AI 特殊規範**

**引用完整性原則**：所有生成的法律文本必須附帶可驗證的條文引用，禁止使用「依相關法規」等模糊表述。每個引用必須包含：法典名稱、條號、項次（如有）、生效版本。

**幻覺防護原則**：所有法律條文的生成必須經過 CitationVerificationAgent 的驗證，驗證失敗的回應必須標記 UNVERIFIED 並附帶警告說明，嚴禁直接輸出未驗證的法律引用。

**時效敏感性原則**：涉及消滅時效、除斥期間的計算必須使用 DeadlineCalendar 的知識庫（src/legal\_kb/limitation\_periods.py），禁止 LLM 自行計算時效，Hard Gate 閾值為零容忍（\= 1.00）。

**視窗代碼輸出禁令**：嚴禁在聊天對話視窗輸出超過 50 行的完整程式碼區塊，防止 KV Cache 爆炸。所有程式碼變更必須靜默呼叫原生檔案寫入工具處理。

**資料最小化原則**：日誌中禁止記錄姓名、身分證字號、案件當事人等敏感資訊，統一以 \[REDACTED\] 替代。

**C4. Git 提交規範**

feat(agent-①): 新增糾錯排版功能

fix(eval-gate): 修復幻覺率計算邏輯

perf(vector): HNSW 索引效能優化

test(gates): 新增時效計算測試案例

skill(s03): 更新 limitation-calculator Skill

docs(api): 更新 OpenAPI 規格

**C5. 除錯回滾協議**

若連續 3 輪除錯 Bug 未減或發生錯誤漂移，必須執行 Git Rollback 退回安全綠色節點：

git log \--oneline \-10 \# 查看最近 10 個提交

git rollback \<safe-commit-sha\> \# 退回安全節點

**CLAUDE.md — 硬體防禦紅線協議**

**CL1. 硬體資源分流鐵律**

// config.json — 單一真理源 (SSOT)

{

"omp\_num\_threads": "4",

"mkl\_num\_threads": "4",

"chroma\_text\_limit": 150000,

"base\_path": "C:/LocalAI\_Workstation",

"whisper\_gpu\_id": 1,

"chromadb\_gpu\_id": 1,

"ollama\_gpu\_id": 0,

"ollama\_host": "http://localhost:11434",

"ollama\_model": "deepseek-r1:7b"

}

**GPU 任務分流鐵律（不可違反）**：

| 				GPU 			 | 				任務 			 | 				記憶體上限 			 |
| :---- | :---- | :---- |
| 				GPU-0（RTX 				5060 Ti 16GB） 			 | 				Ollama 				推理（DeepSeek-R1:7b） 			 | 				\~5GB 				VRAM 			 |
| 				GPU-1（RTX 				5060 Ti 16GB） 			 | 				ChromaDB 				\+ Whisper \+ Embedding 			 | 				\~12GB 				VRAM 			 |

**CL2. ChromaDB 單例防護**

\# 全域模組級單例（agent\_core\_pro.py）

\_CHROMA\_CLIENTS: dict\[str, chromadb.PersistentClient\] \= {}

def get\_chroma\_client(path: str) \-\> chromadb.PersistentClient:

if path not in \_CHROMA\_CLIENTS:

\_CHROMA\_CLIENTS\[path\] \= chromadb.PersistentClient(path\=path)

return \_CHROMA\_CLIENTS\[path\]

\# Streamlit 層級單例（app.py）

@st.cache\_resource

def get\_legal\_agent() \-\> LocalLegalAgent:

return LocalLegalAgent(config\=load\_config())

**CL3. OOM 斷路器**

\# 每次 Ingestion/對話迴圈末端必須執行

import gc, torch

def \_cleanup\_memory():

gc.collect()

if torch.cuda.is\_available():

torch.cuda.empty\_cache()

**CL4. Windows 特殊設定**

**中文路徑問題**：所有 Python 腳本呼叫必須使用 execFile 而非 exec，確保透過 Windows Unicode API（CreateProcessW/UTF-16）傳遞路徑，避免 CP950 字元集破壞中文路徑。

**靜態資源編碼**：Express 靜態服務必須強制設定 charset=utf-8 標頭，防止瀏覽器以 CP950 解碼 UTF-8 資源導致 Emoji 和中文字元亂碼。

**Vite HMR 設定**：vite.config.ts 必須忽略 .md、.json、.zip、.git 檔案的監控，防止背景寫入操作觸發 EBUSY 鎖定錯誤導致 HMR 崩潰。

**AGENT.md — Agent 行為規範**

**A1. Agent 架構原則**

**單一職責原則（SRP）**：每個 Agent 只負責一項明確的法律任務，禁止在單一 Agent 中混合多種職責。**工具呼叫冪等性**：相同輸入在任何時刻產生相同輸出，向量搜尋固定隨機種子，LLM 呼叫使用 temperature=0 或快取確保一致性。**失敗快速原則**：Agent 在遇到 Hard Gate 失敗時必須立即停止並返回錯誤。

**A2. 標準工具呼叫格式**

\# Agent ⑧ RAG 查詢標準格式

result \= await rag\_query(

question\=normalize\_legal\_query(raw\_question),

case\_id\=current\_case\_id, \# 案件上下文

top\_k\=10,

filters\={"jurisdiction": "taiwan"},

dense\_weight\=0.7,

sparse\_weight\=0.3,

max\_retrieval\_rounds\=3, \# Agentic RAG 最大輪數

)

\# Agent ④ 時效計算標準格式

result \= await calculate\_limitation(

cause\_of\_action\="侵權行為損害賠償",

incident\_date\="2024-01-15",

discovery\_date\="2024-03-01", \# 知悉日（主觀起算點）

jurisdiction\="taiwan",

)

**A3. 記憶體架構**

| 				記憶體類型 			 | 				儲存後端 			 | 				TTL 			 | 				用途 			 |
| :---- | :---- | :---- | :---- |
| 				短期記憶（Session） 			 | 				Redis 			 | 				3600s 			 | 				當前對話上下文、已驗證引用 			 |
| 				長期記憶（Persistent） 			 | 				cases\_data.json 			 | 				永久 			 | 				案件資料、關係人、時間線 			 |
| 				向量記憶（Semantic） 			 | 				ChromaDB 			 | 				永久 			 | 				教材嵌入、法條向量 			 |
| 				去重記憶（Idempotency） 			 | 				ingested\_history.json 			 | 				永久 			 | 				SHA-256 				去重記錄 			 |

**A4. 完整環境變數清單**

\# LLM 設定

OLLAMA\_HOST\=http://localhost:11434

OLLAMA\_MODEL\=deepseek-r1:7b

OPENAI\_API\_KEY\=sk-... \# Cloud LLM Fallback

ANTHROPIC\_API\_KEY\=sk-ant-... \# Cloud LLM Fallback

\# GPU 分流

OLLAMA\_GPU\_ID\=0

CHROMADB\_GPU\_ID\=1

WHISPER\_GPU\_ID\=1

OMP\_NUM\_THREADS\=4

MKL\_NUM\_THREADS\=4

\# 資料庫

DATABASE\_URL\=postgresql://legal\_user:${DB\_PASS}@localhost:5432/legal\_db

REDIS\_URL\=redis://localhost:6379/0

CHROMA\_TEXT\_LIMIT\=150000

\# Eval Gates 閾值

CITATION\_ACCURACY\_THRESHOLD\=0.95

HALLUCINATION\_RATE\_THRESHOLD\=0.05

LIMITATION\_ACCURACY\_THRESHOLD\=1.00

P95\_LATENCY\_THRESHOLD\_MS\=3000

COMPOSITE\_SCORE\_THRESHOLD\=0.88

\# 監控

PROMETHEUS\_PORT\=9090

GRAFANA\_PORT\=3001

SLACK\_WEBHOOK\_URL\=https://hooks.slack.com/...

**六、本地 AI 法律工作站完整部署架構圖**

**6.1 服務清單與端口規劃**

| 				服務 			 | 				程式碼入口 			 | 				端口 			 | 				記憶體 			 | 				GPU 			 | 				說明 			 |
| :---- | :---- | :---- | :---- | :---- | :---- |
| 				React 				\+ Vite SPA 			 | 				src/App.tsx 			 | 				3000 			 | 				512MB 			 | 				— 			 | 				前端 5 				個 				Tab 			 |
| 				Node.js/Express 			 | 				server.ts 			 | 				3000 			 | 				1GB 			 | 				— 			 | 				API 				閘道 				\+ 				Unicode 橋接 			 |
| 				Vite 				HMR 			 | 				vite.config.ts 			 | 				24678 			 | 				— 			 | 				— 			 | 				開發模式熱更新 			 |
| 				FastAPI 			 | 				src/api/main.py 			 | 				8080 			 | 				2GB 			 | 				— 			 | 				OpenAPI 				3.1 			 |
| 				Streamlit 			 | 				app.py 			 | 				8501 			 | 				4GB 			 | 				— 			 | 				RAG 				對話主介面 			 |
| 				Ollama 			 | 				— 			 | 				11434 			 | 				\~5GB 				VRAM 			 | 				GPU-0 			 | 				DeepSeek-R1:7b 			 |
| 				ChromaDB 			 | 				agent\_core\_pro.py 			 | 				內嵌 			 | 				\~8GB 				VRAM 			 | 				GPU-1 			 | 				向量知識庫 			 |
| 				Whisper 			 | 				auto\_ingest\_bot.py 			 | 				內嵌 			 | 				\~4GB 				VRAM 			 | 				GPU-1 			 | 				STT，最大並行 				2 			 |
| 				PostgreSQL 			 | 				— 			 | 				5432 			 | 				16GB 			 | 				— 			 | 				結構化資料 \+ 				pgvector 			 |
| 				Redis 			 | 				— 			 | 				6379 			 | 				4GB 			 | 				— 			 | 				快取 \+ 				Celery Broker 			 |
| 				Qdrant 			 | 				— 			 | 				6333/6334 			 | 				32GB 			 | 				— 			 | 				雲端/擴展向量 				DB 			 |
| 				Prometheus 			 | 				— 			 | 				9090 			 | 				2GB 			 | 				— 			 | 				指標收集 			 |
| 				Grafana 			 | 				— 			 | 				3001 			 | 				1GB 			 | 				— 			 | 				7 				個監控面板 			 |

**6.2 一鍵部署指令**

\# Windows 雙擊執行

全自動吸收教材.bat

\# 或 PowerShell 手動啟動

cd C:\\Users\\temp\\antigravity\\LexMind-Omni-法律實務\-AI-工作站

\# Step 1: 安裝依賴

pnpm install \# 256 個 Node.js 套件

pip install \-r requirements.txt \# Python 依賴

\# Step 2: 啟動 Ollama

ollama serve

ollama pull deepseek-r1:7b

\# Step 3: 啟動全端系統

npm run dev \# Express \+ Vite → localhost:3000

\# Step 4: 啟動 Streamlit（選用）

python \-m streamlit run app.py \--server.port 8501

\# Step 5: 執行評測

make eval-fast \# 快速 Hard Gate 評測（\< 10 分鐘）

make eval \# 完整七維度評測

**七、Workflow 細節規範：五大核心流程**

**7.1 教材吸收 Workflow（全自動）**

**觸發方式**：雙擊 全自動吸收教材.bat 或排程任務（每日 02:00）。

**完整流程**：

\[磁碟掃描\] Agent② scan\_all\_drives()

↓ 遍歷 A-Z，過濾系統資料夾，匹配法律關鍵字

\[快取寫入\] chosen\_paths\_buffer.json

↓ 前端重新整理後可見

\[ETA 計算\] estimate\_processing\_time()

↓ 投影預估開始/結束時間

\[批次處理\] 每批 N 個檔案，間隔 X 秒（可配置）

↓ 支援 Pause / Resume / Abort

\[多模態解析\] Agent⑥ ingest\_to\_chroma()

├── mp4/mp3/wav → Whisper STT (GPU-1) → Ollama 校正 (GPU-0)

├── pdf → PyPDF2 \+ OCR → Ollama 校正

└── txt → 直接讀取截斷 150,000 字

\[SHA-256 去重\] ingested\_history.json 比對

↓ 已存在 → Skip；新增 → upsert

\[向量入庫\] ChromaDB upsert (GPU-1)

↓ 科目前綴命名：\[科目\]\_\[章節\]\_\[原檔名\]

\[OOM 清理\] gc.collect() \+ cuda.empty\_cache()

\[日誌記錄\] ingest\_errors.log（錯誤時）

**7.2 RAG 法律諮詢 Workflow**

**觸發方式**：使用者在 Streamlit 或 Web UI 輸入法律問題。

\[輸入正規化\] normalize\_legal\_query()

↓ 全形→半形、條文格式標準化、法典縮寫展開

\[RWS 加權\] rws\_weight\_engine()

↓ 計算法律位階權重；時效關鍵字→強制拉滿

\[Agentic RAG 規劃\] \_plan\_retrieval()

↓ 制定多步檢索策略

\[混合搜尋\] hybrid\_search()（最多 3 輪）

├── Dense 向量搜尋（ChromaDB，GPU-1，weight=0.7）

├── BM25 關鍵字搜尋（Sparse，weight=0.3）

└── RRF 融合（k=60）

\[品質評估\] \_evaluate\_retrieval\_quality()

↓ NDCG@5 \< 0.7 → 重新措辭查詢

\[案件背景整合\] Agent⑦ get\_case\_context()

\[Prompt 組裝\] 法律位階 \+ 案情 \+ 法條 \+ 時效警示

\[LLM 生成\] Ollama DeepSeek-R1:7b (GPU-0)

↓ temperature=0（條文引用）/ 0.3（分析）

\[引用驗證\] Agent① check\_citation\_format()

\[Eval Gates\] 七維度評測

\[輸出\] 含法源引用 \+ 信心分數 \+ 時效警示（如適用）

**7.3 書狀生成 Workflow**

\[律師指定\] 書狀類型 \+ 主張清單 \+ case\_id

↓

\[案件上下文\] Agent⑦ get\_case\_context()

↓ 關係人 \+ 爭點 \+ 證物 \+ 時間線

\[法理依據\] Agent⑧ rag\_query()

↓ 相關法條 \+ 判決先例

\[書狀生成\] Agent⑨ draft\_pleading()

↓ Ollama LLM，temperature=0.5

\[自動校對\] Agent① format\_legal\_doc()

↓ 錯字校正 \+ 格式美化 \+ 引用驗證

\[Eval Gate\] 書狀格式合規 Soft Gate ≥ 0.85

↓ 失敗 → 重新生成

\[輸出\] 標準書狀（起訴狀/答辯狀/聲請書）

**7.4 CI/CD 評測 Workflow（五階段）**

Stage 1: 靜態分析（\< 5 min）

├── python \-m py\_compile app.py agent\_core\_pro.py

├── ruff check . && mypy \--strict

└── bandit \-ll \-r scripts/

Stage 2: Legal Eval Gates（\< 30 min）

├── Hard Gate ①: 法條引用準確性 ≥ 0.95

├── Hard Gate ②: 幻覺率 \< 0.05

├── Hard Gate ③: 時效計算 \= 1.00

├── Hard Gate ④: P95 延遲 \< 3000ms

├── Hard Gate ⑤: 冪等性 \= 1.00

├── Soft Gate ①: 書狀格式 ≥ 0.85

├── Soft Gate ②: NDCG@5 ≥ 0.80

└── Composite Score ≥ 0.88 → PASS

Stage 3: 整合測試（\< 45 min）

├── test\_dedup.py（去重冪等性）

├── test\_streamlit\_bot.py（WebSocket 穩定性）

└── E2E 黃金資料集回歸（4 法律類別）

Stage 4: 報告生成（\< 5 min）

├── HTML 評測報告

├── PR 留言自動更新

└── Slack 通知

Stage 5: Deploy Guard

├── Pre-Deploy Gate（與基準值比較，容忍度 ±2%）

├── 金絲雀部署（10% → 25% → 50% → 100%）

└── 自動回滾（錯誤率 \> 5% 或延遲 \> 3500ms）

**7.5 時效警示 Workflow（RWS 觸發）**

\[關鍵字偵測\] check\_rws\_trigger(text)

命中：消滅時效 / 追訴權時效 / 除斥期間 / 罹於時效

↓

\[強制 RWS 拉滿\] 所有法律位階權重設為最高

↓

\[時效計算\] DeadlineCalendar.calculate\_limitation()

→ 查詢 limitation\_periods.py 知識庫

→ 計算截止日期 \+ 剩餘天數

↓

\[警示生成\] format\_warning\_header()

→ 首段輸出粗體紅字警示：

「⚠️ 時效警示：本案涉及消滅時效，

依民法第XXX條，時效期間為X年，

截止日期為XXXX年XX月XX日（距今剩X天）」

↓

\[Hard Gate 驗證\] 時效計算正確性 \= 1.00

**八、法律 SLA 標準與效能基準**

**8.1 Legal Eval Gates 閾值矩陣**

| 				閘門 			 | 				類型 			 | 				指標 			 | 				開發閾值 			 | 				生產閾值 			 | 				失敗行為 			 | 				對應程式碼 			 |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| 				法條引用準確性 			 | 				Hard 			 | 				≥ 0.95 			 | 				≥ 0.95 			 | 				≥ 0.97 			 | 				Block 				PR 			 | 				citation\_hallucination.py 			 |
| 				幻覺率 			 | 				Hard 			 | 				\< 				0.05 			 | 				\< 				0.05 			 | 				\< 				0.03 			 | 				Block 				PR 			 | 				citation\_hallucination.py 			 |
| 				時效計算正確性 			 | 				Hard 			 | 				\= 				1.00 			 | 				\= 				1.00 			 | 				\= 				1.00 			 | 				Block 				PR 			 | 				statute\_format\_retrieval.py 			 |
| 				回應延遲 P95 			 | 				Hard 			 | 				\< 				3000ms 			 | 				\< 				3000ms 			 | 				\< 				2000ms 			 | 				Block 				PR 			 | 				latency\_idempotency.py 			 |
| 				冪等性 			 | 				Hard 			 | 				\= 				1.00 			 | 				\= 				1.00 			 | 				\= 				1.00 			 | 				Block 				PR 			 | 				latency\_idempotency.py 			 |
| 				書狀格式合規 			 | 				Soft 			 | 				≥ 0.85 			 | 				≥ 0.80 			 | 				≥ 0.85 			 | 				Warn 			 | 				statute\_format\_retrieval.py 			 |
| 				檢索相關性 NDCG@5 			 | 				Soft 			 | 				≥ 0.80 			 | 				≥ 0.75 			 | 				≥ 0.80 			 | 				Warn 			 | 				eval\_gates.py 			 |
| 				**綜合分數** 			 | 				Composite 			 | 				≥ **0.88** 			 | 				≥ **0.70** 			 | 				≥ **0.88** 			 | 				**Block 				Deploy** 			 | 				eval\_gates.py 			 |

**8.2 效能 SLA 目標**

| 				指標 			 | 				開發目標 			 | 				生產 SLA 			 | 				實測值（參考） 			 |
| :---- | :---- | :---- | :---- |
| 				Ollama 				連線延遲 			 | 				\< 				100ms 			 | 				\< 				50ms 			 | 				**34ms**（實測） 			 |
| 				RAG 				查詢 				P50 			 | 				\< 				1500ms 			 | 				\< 				1000ms 			 | 				— 			 |
| 				RAG 				查詢 				P95 			 | 				\< 				3000ms 			 | 				\< 				2000ms 			 | 				— 			 |
| 				Whisper 				轉錄速度 			 | 				\~14 				min/檔 			 | 				— 			 | 				**\~14 				min**（雙 				GPU 				實測） 			 |
| 				系統可用性 			 | 				99.5% 			 | 				99.9% 			 | 				— 			 |
| 				CI 				執行時間 			 | 				\< 				30 min 			 | 				— 			 | 				— 			 |
| 				向量索引 Recall@10 			 | 				≥ 95% 			 | 				≥ 97% 			 | 				— 			 |
| 				向量索引 P95 				延遲 			 | 				\< 				100ms 			 | 				\< 				50ms 			 | 				— 			 |

**8.3 Makefile 常用指令**

\# 開發

make dev \# 啟動開發環境

make test \# 執行完整測試套件（46 個測試案例）

make test-unit \# 僅執行單元測試

make eval-fast \# 快速 Hard Gate 評測（\< 10 分鐘）

make eval \# 完整七維度評測（\< 30 分鐘）

make lint \# ruff \+ mypy \+ bandit \+ eslint

\# 部署

make deploy \# 生產環境完整部署

make rollback \# 回滾至上一個版本

\# 資料管理

make ingest \# 啟動全自動教材吸收

make build-index \# 建立向量索引

make benchmark \# 效能基準測試

\# 監控

make health \# 服務健康檢查

make logs \# 顯示最近 100 行日誌

make metrics \# 顯示當前效能指標

**參考文獻**

## 參考文獻

[\[1\] Anthropic — Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)  
[\[2\] Google Cloud — Choose a design pattern for your agentic AI system](https://cloud.google.com/architecture/choose-design-pattern-agentic-ai-system)  
[\[3\] Harvey AI — Introducing Harvey Agents](https://github.com/harvey-ai/harvey-agents)  
[\[4\] Anthropic — Claude Code Best Practices for Large Codebases](https://www.anthropic.com/engineering/claude-code-best-practices)  
[\[5\] Qdrant — Quantization Documentation](https://qdrant.tech/documentation/manage-data/quantization/)  
[\[6\] HNSW at Scale: Why Your RAG System Gets Worse as the Vector Database Grows](https://towardsdatascience.com/hnsw-at-scale-why-your-rag-system-gets-worse-as-the-vector-database-grows/)  
