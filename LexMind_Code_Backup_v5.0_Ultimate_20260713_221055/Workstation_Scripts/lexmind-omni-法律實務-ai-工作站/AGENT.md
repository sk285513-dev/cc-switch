# AGENT.md — Agent 行為規範
A1. Agent 架構原則

單一職責原則（SRP）：每個 Agent 只負責一項明確的法律任務，禁止在單一 Agent 中混合多種職責。工具呼叫冪等性：相同輸入在任何時刻產生相同輸出，向量搜尋固定隨機種子，LLM 呼叫使用 temperature=0 或快取確保一致性。失敗快速原則：Agent 在遇到 Hard Gate 失敗時必須立即停止並返回錯誤。

A2. 標準工具呼叫格式

# Agent ⑧ RAG 查詢標準格式

result = await rag_query(

question=normalize_legal_query(raw_question),

case_id=current_case_id, # 案件上下文

top_k=10,

filters={"jurisdiction": "taiwan"},

dense_weight=0.7,

sparse_weight=0.3,

max_retrieval_rounds=3, # Agentic RAG 最大輪數

)

# Agent ④ 時效計算標準格式

result = await calculate_limitation(

cause_of_action="侵權行為損害賠償",

incident_date="2024-01-15",

discovery_date="2024-03-01", # 知悉日（主觀起算點）

jurisdiction="taiwan",

)

A3. 記憶體架構

記憶體類型

儲存後端

TTL

用途

短期記憶（Session）

Redis

3600s

當前對話上下文、已驗證引用

長期記憶（Persistent）

cases_data.json

永久

案件資料、關係人、時間線

向量記憶（Semantic）

ChromaDB

永久

教材嵌入、法條向量

去重記憶（Idempotency）

ingested_history.json

永久

SHA-256 去重記錄

A4. 完整環境變數清單

# LLM 設定

OLLAMA_HOST=http://localhost:11434

OLLAMA_MODEL=deepseek-r1:7b

OPENAI_API_KEY=sk-... # Cloud LLM Fallback

ANTHROPIC_API_KEY=sk-ant-... # Cloud LLM Fallback

# GPU 分流

OLLAMA_GPU_ID=0

CHROMADB_GPU_ID=1

WHISPER_GPU_ID=1

OMP_NUM_THREADS=4

MKL_NUM_THREADS=4

# 資料庫

DATABASE_URL=postgresql://legal_user:${DB_PASS}@localhost:5432/legal_db

REDIS_URL=redis://localhost:6379/0

CHROMA_TEXT_LIMIT=150000

# Eval Gates 閾值

CITATION_ACCURACY_THRESHOLD=0.95

HALLUCINATION_RATE_THRESHOLD=0.05

LIMITATION_ACCURACY_THRESHOLD=1.00

P95_LATENCY_THRESHOLD_MS=3000

COMPOSITE_SCORE_THRESHOLD=0.88

# 監控

PROMETHEUS_PORT=9090

GRAFANA_PORT=3001

SLACK_WEBHOOK_URL=https://hooks.slack.com/...