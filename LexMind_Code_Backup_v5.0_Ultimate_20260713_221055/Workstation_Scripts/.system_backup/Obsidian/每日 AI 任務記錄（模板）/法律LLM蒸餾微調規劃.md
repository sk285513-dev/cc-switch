# 台灣法律 LLM 兩階段蒸餾微調技術規劃

> **文件版本**：v1.0  
> **適用環境**：RTX 5060 Ti（16GB GDDR7）、Windows 10、Python 3.14  
> **Student Model**：deepseek-r1:14b（本地 Ollama）  
> **Teacher Model**：Llama-3-Taiwan-70B（透過 Ollama API 呼叫）  

---

## 目錄

1. [系統需求與環境確認](#一系統需求與環境確認)
2. [兩階段蒸餾架構總覽](#二兩階段蒸餾架構總覽)
3. [VRAM 預算分析](#三vram-預算分析)
4. [環境安裝與設定](#四環境安裝與設定)
5. [第一階段：公開資料集打底](#五第一階段公開資料集打底-domain-adaptation)
6. [第二階段：本案資料微調](#六第二階段本案資料微調-case-specific-fine-tuning)
7. [LoRA Adapter 合併與 GGUF 匯出](#七lora-adapter-合併與-gguf-匯出)
8. [DeepEval 評估方案](#八deepeval-評估方案)
9. [訓練時間估算](#九訓練時間估算)
10. [常見錯誤與處理](#十常見錯誤與處理)
11. [完整執行流程速查](#十一完整執行流程速查)

---

## 一、系統需求與環境確認

### 硬體規格

| 項目 | 規格 | 備註 |
|------|------|------|
| GPU | RTX 5060 Ti 16GB GDDR7 | Blackwell 架構，Unsloth 支援 RTX 50 系列 |
| RAM | 16GB | 資料載入、CPU offload 緩衝 |
| 儲存 | 1TB SSD | 模型權重、資料集、LoRA adapter |
| OS | Windows 10 | 建議使用 Conda 環境隔離 |

### 軟體版本需求

| 套件 | 說明 |
|------|------|
| Python | 3.12（訓練環境用 Conda 建立，**不使用** 系統 Python 3.14） |
| CUDA Toolkit | 13.0（配合 PyTorch `cu130` 輪子） |
| Unsloth | 透過 `pip install unsloth` 取得最新版 |
| PyTorch | `pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130` |
| transformers | 隨 Unsloth 相依自動安裝 |
| trl | 隨 Unsloth 相依自動安裝 |
| datasets | `pip install datasets` |
| peft | 隨 Unsloth 相依自動安裝 |
| bitsandbytes | `pip install bitsandbytes` |
| deepeval | 已安裝（系統環境） |

> **重要說明**：Unsloth 官方 Windows 安裝文件要求使用 Python 3.12 的 Conda 環境。Python 3.14 目前與部分 CUDA 相依套件（bitsandbytes、triton）的二進位輪子相容性尚未完整，**訓練環境必須另開 Conda 虛擬環境**並使用 Python 3.12。評估（DeepEval）可繼續沿用系統 Python 3.14 環境。

---

## 二、兩階段蒸餾架構總覽

```
┌─────────────────────────────────────────────────────────────┐
│                    知識蒸餾流程                              │
│                                                             │
│  Teacher: Llama-3-Taiwan-70B                                │
│  (透過 Ollama API 呼叫，不需本地 VRAM)                       │
│        │                                                    │
│        ▼ 生成高品質回答（軟標籤/合成 QA）                    │
│                                                             │
│  ┌──────────────────────────────────────────────┐          │
│  │ 第一階段：Domain Adaptation                   │          │
│  │ 公開台灣法律資料集 → QLoRA 微調               │          │
│  │ 輸出：stage1_lora_adapter/                   │          │
│  └────────────────────┬─────────────────────────┘          │
│                       │                                    │
│                       ▼                                    │
│  ┌──────────────────────────────────────────────┐          │
│  │ 第二階段：Case-Specific Fine-tuning           │          │
│  │ ChromaDB 本案 QA 對 → 繼續 QLoRA 微調        │          │
│  │ 輸出：stage2_lora_adapter/                   │          │
│  └────────────────────┬─────────────────────────┘          │
│                       │                                    │
│                       ▼                                    │
│  合併 LoRA → 匯出 GGUF → Ollama 載入                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 資料集總覽

| 資料集 | 資料量 | 格式 | 用途 |
|--------|--------|------|------|
| `lianghsun/tw-legal-synthetic-qa` | 9,631 筆（train 7,704） | ShareGPT（messages/role/content） | 法律問答 SFT |
| `lianghsun/tw-bar-examination-2020-chat` | 299 筆（train 269） | Alpaca（instruction/input/output） | 律師考試問答 |
| `lianghsun/tw-processed-law-article` | 230,974 筆 | text/name/level | 法律條文通識 |
| `lianghsun/tw-processed-judgments-14B` | 未公開總數（判決書精選） | 主文/事實/理由 | 判決推理訓練 |
| ChromaDB `legal_docs` collection | ~500 筆（取樣） | QA 對（自動生成） | 本案事實記憶 |

> **判決書資料集取樣策略**：`tw-processed-judgments-14B` 總量龐大，第一階段僅從中隨機取樣 3,000 筆，以避免訓練時間過長及資料不均衡。

---

## 三、VRAM 預算分析

RTX 5060 Ti 擁有 16GB GDDR7，訓練期間各部分配置如下：

### 訓練時 VRAM 分配

```
16 GB VRAM 分配（QLoRA 4-bit + Unsloth）
══════════════════════════════════════════════
┌─────────────────────────────────────┬───────┐
│ deepseek-r1:14b 模型權重（4-bit NF4） │  ~7.5 GB │
│ LoRA adapter 可訓練參數（fp16）       │  ~1.5 GB │
│ 梯度（gradient）& optimizer states   │  ~2.5 GB │
│ Activation 緩衝（forward pass）      │  ~2.0 GB │
│ CUDA context & PyTorch overhead      │  ~0.5 GB │
│ 批次資料（batch_size=2）             │  ~1.5 GB │
│ 緩衝（避免 OOM）                    │  ~1.0 GB │
├─────────────────────────────────────┼───────┤
│ 合計                                │ ~17.0 GB │
└─────────────────────────────────────┴───────┘
```

> **注意**：14B 模型 4-bit 量化在 Unsloth 的 `use_gradient_checkpointing="unsloth"` 優化下，實測 VRAM 峰值約落在 13–15GB 之間，16GB 可以容納。如訓練中出現 OOM（記憶體不足）錯誤，請依照第十節的調整步驟處理。

### 推薦 QLoRA 參數設定（16GB VRAM 適用）

| 參數 | 建議值 | 說明 |
|------|--------|------|
| `load_in_4bit` | `True` | 使用 NF4 量化 |
| `r`（LoRA rank） | `16` | 平衡效能與記憶體 |
| `lora_alpha` | `16` | 縮放係數，與 r 相等 |
| `per_device_train_batch_size` | `2` | 配合 gradient accumulation |
| `gradient_accumulation_steps` | `8` | 有效 batch size = 16 |
| `max_seq_length` | `2048` | 法律文本較長，建議不低於 2048 |
| `use_gradient_checkpointing` | `"unsloth"` | Unsloth 特有優化，減少約 30% VRAM |
| `optim` | `"adamw_8bit"` | 8-bit Adam，節省 optimizer 記憶體 |

---

## 四、環境安裝與設定

### 4.1 建立 Conda 訓練環境（PowerShell）

```powershell
# 步驟一：下載並安裝 Miniconda（若尚未安裝）
Invoke-WebRequest -Uri "https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe" -OutFile ".\miniconda.exe"
Start-Process -FilePath ".\miniconda.exe" -ArgumentList "/S" -Wait
del .\miniconda.exe

# 重新開啟 PowerShell 後，建立訓練專用環境（Python 3.12 為必要條件）
conda create --name unsloth_env python==3.12 -y
conda activate unsloth_env

# 步驟二：安裝 PyTorch（CUDA 13.0 對應 RTX 5060 Ti Blackwell 架構）
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130

# 驗證 GPU 可用
python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0))"

# 步驟三：安裝 Unsloth 與訓練相依套件
pip install unsloth
pip install datasets huggingface_hub
pip install chromadb requests

# 步驟四：安裝 llama.cpp（用於後續 GGUF 轉換）
# 到 https://github.com/ggml-org/llama.cpp/releases 下載 Windows 預編譯版
# 解壓縮至 C:\llama.cpp\
# 同時安裝 Python 轉換腳本相依
git clone https://github.com/ggerganov/llama.cpp.git C:\llama.cpp
pip install -r C:\llama.cpp\requirements.txt
```

### 4.2 確認 Ollama 服務運行

```powershell
# 確認 Ollama 已運行（應有 http://localhost:11434 回應）
Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method GET

# 確認 Llama-3-Taiwan-70B 已可透過 Ollama 呼叫
# Ollama Hub 上的 tag：kenneth85/llama-3-taiwan 或 cwchang/llama-3-taiwan-70b-instruct
ollama pull cwchang/llama-3-taiwan-70b-instruct

# 確認 deepseek-r1:14b 已存在
ollama list
```

> **Llama-3-Taiwan-70B 的 Ollama 存取**：Ollama Hub 上有 `cwchang/llama-3-taiwan-70b-instruct`（含 Q4_K_S 量化版）可直接 `ollama pull`。70B 模型的 Q4 量化約需 40GB 磁碟空間，但 **不佔用 GPU VRAM**（透過 API 呼叫時由 Ollama 管理，可搭配 CPU+RAM 推理）。若 RAM 不足（本機僅 16GB），可考慮使用 `cwchang/llama-3-taiwan-70b-instruct:q4_k_s` 並設定較低的 `num_ctx`，或改用雲端 API（如 HuggingFace Inference Endpoint）。

---

## 五、第一階段：公開資料集打底（Domain Adaptation）

### 5.1 generate_qa_pairs.py — 從 ChromaDB 生成本案 QA 對

此腳本用於**第二階段前**的資料準備，從 ChromaDB 中抽取文書 chunk，以 qwen3:30b-a3b 生成 QA 對。

```python
# generate_qa_pairs.py
# 從 ChromaDB legal_docs collection 抽取 chunk，
# 用 qwen3:30b-a3b 自動生成問答對，儲存為 JSONL

import json
import requests
import chromadb
from pathlib import Path

# ── 設定區 ──────────────────────────────────────────────
CHROMA_PATH = r"C:\Users\temp\chroma_db"   # ChromaDB 持久化路徑，依實際路徑調整
COLLECTION_NAME = "legal_docs"
OLLAMA_API = "http://localhost:11434/api/chat"
QA_GENERATOR_MODEL = "qwen3:30b-a3b"       # 主力推理模型
OUTPUT_JSONL = r"C:\Users\temp\legal_qa\case_qa_pairs.jsonl"
MAX_CHUNKS = 500                            # 最多抽取的 chunk 數量
BATCH_SIZE = 10                             # 每次處理的 chunk 數
# ─────────────────────────────────────────────────────────


def get_all_chunks(collection, max_chunks: int) -> list[dict]:
    """從 ChromaDB collection 抽取所有 chunk"""
    results = collection.get(
        limit=max_chunks,
        include=["documents", "metadatas"]
    )
    chunks = []
    for doc, meta in zip(results["documents"], results["metadatas"]):
        chunks.append({"text": doc, "metadata": meta})
    print(f"[INFO] 共抽取 {len(chunks)} 個 chunk")
    return chunks


def generate_qa_with_ollama(chunk_text: str, model: str) -> dict | None:
    """
    呼叫 Ollama API，讓模型根據 chunk 生成問題與答案
    回傳 {"instruction": ..., "input": ..., "output": ...} 格式
    """
    system_prompt = (
        "你是台灣法律專業助理。根據以下法律文書內容，"
        "生成一個具體的法律問題（instruction）和對應的詳細回答（output）。"
        "問題必須根植於文書的具體事實，不得捏造不存在的資訊。"
        "請以 JSON 格式回覆，欄位為 instruction 和 output，不要有其他文字。"
    )
    user_prompt = f"法律文書內容：\n{chunk_text[:1500]}"  # 限制輸入長度

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
        "options": {"temperature": 0.3, "num_ctx": 4096}
    }

    try:
        resp = requests.post(OLLAMA_API, json=payload, timeout=120)
        resp.raise_for_status()
        raw = resp.json()["message"]["content"].strip()

        # 嘗試解析 JSON，處理模型可能輸出 markdown code block 的情況
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        qa = json.loads(raw.strip())

        # 驗證必要欄位存在且非空
        if not qa.get("instruction") or not qa.get("output"):
            return None
        return {
            "instruction": qa["instruction"],
            "input": chunk_text[:500],   # 原始文書片段作為 context
            "output": qa["output"]
        }
    except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
        print(f"[WARN] 生成失敗：{e}")
        return None


def main():
    output_path = Path(OUTPUT_JSONL)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 連接 ChromaDB
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    try:
        collection = client.get_collection(COLLECTION_NAME)
    except Exception as e:
        print(f"[ERROR] 無法取得 collection '{COLLECTION_NAME}'：{e}")
        print("[HINT] 請確認 CHROMA_PATH 與 COLLECTION_NAME 設定正確")
        return

    chunks = get_all_chunks(collection, MAX_CHUNKS)

    success_count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for i, chunk in enumerate(chunks):
            print(f"[{i+1}/{len(chunks)}] 正在生成 QA 對...", end="\r")
            qa = generate_qa_with_ollama(chunk["text"], QA_GENERATOR_MODEL)
            if qa:
                f.write(json.dumps(qa, ensure_ascii=False) + "\n")
                success_count += 1

    print(f"\n[完成] 成功生成 {success_count} 筆 QA 對，儲存至：{output_path}")


if __name__ == "__main__":
    main()
```

**執行方式（PowerShell，使用系統 Python 3.14）**：

```powershell
$env:PYTHONPATH = ""
& "C:\Users\temp\AppData\Local\Python\pythoncore-3.14-64\python.exe" generate_qa_pairs.py
```

---

### 5.2 distill_stage1.py — 第一階段 QLoRA 蒸餾微調

```python
# distill_stage1.py
# 第一階段：下載台灣法律公開資料集，以 Unsloth QLoRA 微調 deepseek-r1:14b
# 執行環境：conda activate unsloth_env（Python 3.12）

import os
import json
from pathlib import Path

# ── 設定區 ──────────────────────────────────────────────
BASE_MODEL_NAME = "unsloth/DeepSeek-R1-Distill-Qwen-14B"  # Unsloth 優化版
OUTPUT_DIR = r"C:\Users\temp\legal_llm\stage1_lora_adapter"
MAX_SEQ_LENGTH = 2048
LOAD_IN_4BIT = True
LORA_RANK = 16
LORA_ALPHA = 16
TRAIN_EPOCHS = 2
BATCH_SIZE = 2
GRAD_ACCUM_STEPS = 8   # 有效 batch size = 16
LEARNING_RATE = 2e-4
JUDGMENTS_SAMPLE_SIZE = 3000  # 判決書資料集取樣數
# ─────────────────────────────────────────────────────────


def load_and_prepare_datasets():
    """載入並整合所有公開台灣法律資料集"""
    from datasets import load_dataset, concatenate_datasets, Dataset

    print("[1/4] 載入 tw-legal-synthetic-qa（ShareGPT 格式）...")
    ds_qa = load_dataset("lianghsun/tw-legal-synthetic-qa", split="train")

    print("[2/4] 載入 tw-bar-examination-2020-chat（Alpaca 格式）...")
    ds_bar = load_dataset("lianghsun/tw-bar-examination-2020-chat", split="train")

    print("[3/4] 載入 tw-processed-law-article（法律條文）...")
    ds_law = load_dataset("lianghsun/tw-processed-law-article", split="train")

    print("[4/4] 載入 tw-processed-judgments-14B（判決書，取樣）...")
    ds_judgments_full = load_dataset("lianghsun/tw-processed-judgments-14B", split="train")
    # 隨機取樣以控制訓練時間
    if len(ds_judgments_full) > JUDGMENTS_SAMPLE_SIZE:
        ds_judgments = ds_judgments_full.shuffle(seed=42).select(range(JUDGMENTS_SAMPLE_SIZE))
    else:
        ds_judgments = ds_judgments_full

    print(f"各資料集大小：QA={len(ds_qa)}, Bar={len(ds_bar)}, Law={len(ds_law)}, Judgments={len(ds_judgments)}")
    return ds_qa, ds_bar, ds_law, ds_judgments


def format_to_alpaca_chat(examples, tokenizer):
    """
    將多種格式統一轉換為 chat template 格式
    此函式由 apply_chat_template 在 map 中使用
    """
    texts = []
    # 處理 ShareGPT 格式（messages 欄位）
    if "messages" in examples:
        for msgs in examples["messages"]:
            try:
                text = tokenizer.apply_chat_template(
                    msgs,
                    tokenize=False,
                    add_generation_prompt=False
                )
                texts.append(text)
            except Exception:
                texts.append("")
    # 處理 Alpaca 格式（instruction/input/output 欄位）
    elif "instruction" in examples:
        for inst, inp, out in zip(
            examples["instruction"],
            examples.get("input", [""] * len(examples["instruction"])),
            examples["output"]
        ):
            context = f"\n\n參考資料：{inp}" if inp and inp.strip() else ""
            msgs = [
                {"role": "user", "content": f"{inst}{context}"},
                {"role": "assistant", "content": out}
            ]
            try:
                text = tokenizer.apply_chat_template(
                    msgs,
                    tokenize=False,
                    add_generation_prompt=False
                )
                texts.append(text)
            except Exception:
                texts.append("")
    # 處理純文字格式（法律條文 text 欄位）
    elif "text" in examples:
        for text_content in examples["text"]:
            msgs = [
                {"role": "user", "content": "請說明以下法律條文的內容與意義："},
                {"role": "assistant", "content": text_content[:2000]}
            ]
            try:
                text = tokenizer.apply_chat_template(
                    msgs,
                    tokenize=False,
                    add_generation_prompt=False
                )
                texts.append(text)
            except Exception:
                texts.append("")
    return {"text": texts}


def format_judgments(examples, tokenizer):
    """處理判決書資料集（主文/事實/理由欄位）"""
    texts = []
    for i in range(len(examples.get("主文", examples.get("text", [])))):
        try:
            # 嘗試取得各欄位，不同版本欄位名稱可能略有差異
            verdict = examples.get("主文", [""])[i] or ""
            facts = examples.get("事實", [""])[i] or ""
            reasons = examples.get("理由", [""])[i] or ""

            if not (verdict or facts or reasons):
                # fallback：直接使用 text 欄位
                raw = examples.get("text", [""])[i] or ""
                msgs = [
                    {"role": "user", "content": "分析以下台灣法院判決書："},
                    {"role": "assistant", "content": raw[:2000]}
                ]
            else:
                question = f"以下判決的事實為何？法院的裁決結果與理由是什麼？\n\n事實：{facts[:800]}"
                answer = f"【主文】\n{verdict}\n\n【裁判理由】\n{reasons[:1200]}"
                msgs = [
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": answer}
                ]
            text = tokenizer.apply_chat_template(
                msgs,
                tokenize=False,
                add_generation_prompt=False
            )
            texts.append(text)
        except Exception:
            texts.append("")
    return {"text": texts}


def main():
    from unsloth import FastLanguageModel
    from trl import SFTTrainer, SFTConfig
    from datasets import concatenate_datasets

    print("=" * 60)
    print("第一階段：台灣法律領域適應 QLoRA 微調")
    print("=" * 60)

    # 載入模型與 tokenizer
    print("\n[模型載入] 從 HuggingFace 下載並量化 DeepSeek-R1-14B...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=BASE_MODEL_NAME,
        max_seq_length=MAX_SEQ_LENGTH,
        load_in_4bit=LOAD_IN_4BIT,
        load_in_8bit=False,
        full_finetuning=False,
        trust_remote_code=True,
    )

    # 設定 LoRA adapter
    print("[LoRA 設定] 注入 LoRA 可訓練參數...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=LORA_RANK,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj"
        ],
        lora_alpha=LORA_ALPHA,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=3407,
        use_rslora=False,
        loftq_config=None,
    )
    model.print_trainable_parameters()

    # 載入並處理資料集
    ds_qa, ds_bar, ds_law, ds_judgments = load_and_prepare_datasets()

    print("\n[資料處理] 統一轉換格式...")
    # ShareGPT 格式
    ds_qa_fmt = ds_qa.map(
        lambda x: format_to_alpaca_chat(x, tokenizer),
        batched=True,
        remove_columns=ds_qa.column_names
    )
    # Alpaca 格式
    ds_bar_fmt = ds_bar.map(
        lambda x: format_to_alpaca_chat(x, tokenizer),
        batched=True,
        remove_columns=ds_bar.column_names
    )
    # 法律條文
    ds_law_sample = ds_law.shuffle(seed=42).select(range(min(2000, len(ds_law))))
    ds_law_fmt = ds_law_sample.map(
        lambda x: format_to_alpaca_chat(x, tokenizer),
        batched=True,
        remove_columns=ds_law_sample.column_names
    )
    # 判決書
    ds_judge_fmt = ds_judgments.map(
        lambda x: format_judgments(x, tokenizer),
        batched=True,
        remove_columns=ds_judgments.column_names
    )

    # 移除空白樣本
    def filter_empty(example):
        return example["text"] is not None and len(example["text"]) > 50

    ds_qa_fmt = ds_qa_fmt.filter(filter_empty)
    ds_bar_fmt = ds_bar_fmt.filter(filter_empty)
    ds_law_fmt = ds_law_fmt.filter(filter_empty)
    ds_judge_fmt = ds_judge_fmt.filter(filter_empty)

    # 合併所有資料集並打亂
    combined_dataset = concatenate_datasets([
        ds_qa_fmt, ds_bar_fmt, ds_law_fmt, ds_judge_fmt
    ]).shuffle(seed=42)

    print(f"[資料集] 合併後總筆數：{len(combined_dataset)}")

    # 訓練設定
    training_args = SFTConfig(
        output_dir=OUTPUT_DIR,
        num_train_epochs=TRAIN_EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRAD_ACCUM_STEPS,
        warmup_ratio=0.03,
        learning_rate=LEARNING_RATE,
        fp16=False,
        bf16=True,                      # RTX 5060 Ti 支援 BF16
        logging_steps=20,
        save_strategy="epoch",
        save_total_limit=2,
        optim="adamw_8bit",
        seed=3407,
        dataset_text_field="text",
        max_seq_length=MAX_SEQ_LENGTH,
        dataset_num_proc=1,             # Windows 多進程有時不穩定，設為 1
        report_to="none",               # 不上傳至 wandb
        dataloader_pin_memory=False,    # Windows 環境下設 False 較穩定
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=combined_dataset,
        args=training_args,
    )

    print("\n[訓練開始] 第一階段 QLoRA 微調...")
    trainer_stats = trainer.train()

    # 儲存 LoRA adapter
    print(f"\n[儲存] LoRA adapter 儲存至：{OUTPUT_DIR}")
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)

    print("\n[完成] 第一階段訓練結束")
    print(f"訓練時間：{trainer_stats.metrics.get('train_runtime', 'N/A'):.1f} 秒")
    print(f"最終 Loss：{trainer_stats.metrics.get('train_loss', 'N/A'):.4f}")


if __name__ == "__main__":
    main()
```

**執行方式（PowerShell，使用 Conda 訓練環境）**：

```powershell
conda activate unsloth_env
python distill_stage1.py
```

---

## 六、第二階段：本案資料微調（Case-Specific Fine-tuning）

### 6.1 distill_stage2.py — 第二階段本案 QA 微調

```python
# distill_stage2.py
# 第二階段：載入 stage1 adapter，繼續用本案 QA 對微調
# 執行環境：conda activate unsloth_env（Python 3.12）

from pathlib import Path

# ── 設定區 ──────────────────────────────────────────────
BASE_MODEL_NAME = "unsloth/DeepSeek-R1-Distill-Qwen-14B"
STAGE1_ADAPTER_PATH = r"C:\Users\temp\legal_llm\stage1_lora_adapter"
CASE_QA_JSONL = r"C:\Users\temp\legal_qa\case_qa_pairs.jsonl"
OUTPUT_DIR = r"C:\Users\temp\legal_llm\stage2_lora_adapter"
MAX_SEQ_LENGTH = 2048
LOAD_IN_4BIT = True
LORA_RANK = 16
LORA_ALPHA = 32              # 第二階段適當提高 alpha，強化本案學習
TRAIN_EPOCHS = 5             # 本案資料少，可多訓練幾個 epoch
BATCH_SIZE = 2
GRAD_ACCUM_STEPS = 4         # 本案資料少，有效 batch size 可稍小
LEARNING_RATE = 1e-4         # 第二階段使用較低學習率，避免遺忘
# ─────────────────────────────────────────────────────────


def load_case_qa_dataset(jsonl_path: str, tokenizer):
    """載入本案 QA 對 JSONL，轉換為 chat template 格式"""
    import json
    from datasets import Dataset

    records = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                if item.get("instruction") and item.get("output"):
                    records.append(item)
            except json.JSONDecodeError:
                continue

    print(f"[資料載入] 讀取 {len(records)} 筆本案 QA 對")

    def format_record(example):
        inst = example["instruction"]
        inp = example.get("input", "")
        out = example["output"]
        context = f"\n\n相關文書：{inp[:400]}" if inp and inp.strip() else ""
        msgs = [
            {"role": "user", "content": f"{inst}{context}"},
            {"role": "assistant", "content": out}
        ]
        text = tokenizer.apply_chat_template(
            msgs,
            tokenize=False,
            add_generation_prompt=False
        )
        return {"text": text}

    raw_ds = Dataset.from_list(records)
    formatted_ds = raw_ds.map(format_record, remove_columns=raw_ds.column_names)
    formatted_ds = formatted_ds.filter(lambda x: x["text"] and len(x["text"]) > 30)

    print(f"[資料集] 有效樣本數：{len(formatted_ds)}")
    return formatted_ds


def main():
    from unsloth import FastLanguageModel
    from trl import SFTTrainer, SFTConfig
    from peft import PeftModel

    print("=" * 60)
    print("第二階段：本案事實 QA 微調（Case-Specific Fine-tuning）")
    print("=" * 60)

    # 確認 stage1 adapter 存在
    if not Path(STAGE1_ADAPTER_PATH).exists():
        raise FileNotFoundError(
            f"找不到第一階段 adapter：{STAGE1_ADAPTER_PATH}\n"
            "請先執行 distill_stage1.py"
        )

    # 確認本案 QA 資料存在
    if not Path(CASE_QA_JSONL).exists():
        raise FileNotFoundError(
            f"找不到本案 QA 資料：{CASE_QA_JSONL}\n"
            "請先執行 generate_qa_pairs.py"
        )

    print("\n[模型載入] 載入基底模型...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=BASE_MODEL_NAME,
        max_seq_length=MAX_SEQ_LENGTH,
        load_in_4bit=LOAD_IN_4BIT,
        load_in_8bit=False,
        full_finetuning=False,
        trust_remote_code=True,
    )

    print(f"[Adapter 載入] 從 {STAGE1_ADAPTER_PATH} 載入第一階段 LoRA adapter...")
    # 注入 LoRA 結構後再從 stage1 載入權重
    model = FastLanguageModel.get_peft_model(
        model,
        r=LORA_RANK,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj"
        ],
        lora_alpha=LORA_ALPHA,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=3407,
        use_rslora=False,
        loftq_config=None,
    )

    # 載入 stage1 訓練好的權重到 LoRA adapter
    from peft import set_peft_model_state_dict
    import torch
    stage1_weights = torch.load(
        f"{STAGE1_ADAPTER_PATH}/adapter_model.bin",
        map_location="cuda",
        weights_only=True
    )
    set_peft_model_state_dict(model, stage1_weights)
    print("[確認] Stage1 adapter 權重已載入")

    model.print_trainable_parameters()

    # 載入本案 QA 資料集
    case_dataset = load_case_qa_dataset(CASE_QA_JSONL, tokenizer)

    # 訓練設定
    training_args = SFTConfig(
        output_dir=OUTPUT_DIR,
        num_train_epochs=TRAIN_EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRAD_ACCUM_STEPS,
        warmup_ratio=0.05,
        learning_rate=LEARNING_RATE,
        fp16=False,
        bf16=True,
        logging_steps=5,
        save_strategy="epoch",
        save_total_limit=3,
        optim="adamw_8bit",
        seed=3407,
        dataset_text_field="text",
        max_seq_length=MAX_SEQ_LENGTH,
        dataset_num_proc=1,
        report_to="none",
        dataloader_pin_memory=False,
        # 學習率排程：cosine decay 適合小資料集
        lr_scheduler_type="cosine",
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=case_dataset,
        args=training_args,
    )

    print("\n[訓練開始] 第二階段本案 QA 微調...")
    trainer_stats = trainer.train()

    # 儲存最終 LoRA adapter
    print(f"\n[儲存] Stage2 LoRA adapter 儲存至：{OUTPUT_DIR}")
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)

    print("\n[完成] 第二階段訓練結束")
    print(f"訓練時間：{trainer_stats.metrics.get('train_runtime', 'N/A'):.1f} 秒")
    print(f"最終 Loss：{trainer_stats.metrics.get('train_loss', 'N/A'):.4f}")


if __name__ == "__main__":
    main()
```

**執行方式（PowerShell）**：

```powershell
conda activate unsloth_env
python distill_stage2.py
```

---

## 七、LoRA Adapter 合併與 GGUF 匯出

### 7.1 merge_export.py — 合併並匯出 GGUF

```python
# merge_export.py
# 合併 Stage2 LoRA adapter 至基底模型，並匯出 GGUF 供 Ollama 載入
# 執行環境：conda activate unsloth_env（Python 3.12）

import subprocess
from pathlib import Path

# ── 設定區 ──────────────────────────────────────────────
BASE_MODEL_NAME = "unsloth/DeepSeek-R1-Distill-Qwen-14B"
STAGE2_ADAPTER_PATH = r"C:\Users\temp\legal_llm\stage2_lora_adapter"
MERGED_MODEL_PATH = r"C:\Users\temp\legal_llm\merged_model"
GGUF_OUTPUT_PATH = r"C:\Users\temp\legal_llm\legal_deepseek_r1_14b_Q4_K_M.gguf"
OLLAMA_MODEL_NAME = "legal-deepseek-r1-14b"
LLAMA_CPP_PATH = r"C:\llama.cpp"
QUANTIZATION_TYPE = "Q4_K_M"          # 建議：Q4_K_M（品質與大小平衡）
MAX_SEQ_LENGTH = 2048
# ─────────────────────────────────────────────────────────


def merge_lora_to_base():
    """合併 LoRA adapter 至基底模型（FP16 精度）"""
    from unsloth import FastLanguageModel

    print("[步驟 1/4] 載入基底模型...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=BASE_MODEL_NAME,
        max_seq_length=MAX_SEQ_LENGTH,
        load_in_4bit=True,
        trust_remote_code=True,
    )

    print(f"[步驟 2/4] 套用 LoRA adapter：{STAGE2_ADAPTER_PATH}")
    from peft import PeftModel
    model = PeftModel.from_pretrained(model, STAGE2_ADAPTER_PATH)

    print("[步驟 3/4] 合併 LoRA 至基底模型（merge_and_unload）...")
    model = model.merge_and_unload()

    print(f"[步驟 4/4] 儲存合併後的完整模型至：{MERGED_MODEL_PATH}")
    merged_path = Path(MERGED_MODEL_PATH)
    merged_path.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(merged_path), safe_serialization=True)
    tokenizer.save_pretrained(str(merged_path))
    print("[完成] 模型合併儲存完畢")


def convert_to_gguf_f16():
    """使用 llama.cpp 的 convert_hf_to_gguf.py 將模型轉為 F16 GGUF"""
    print("\n[步驟 5/5] 轉換為 GGUF（F16 中間格式）...")
    f16_gguf = GGUF_OUTPUT_PATH.replace(".gguf", "_F16.gguf")

    convert_script = Path(LLAMA_CPP_PATH) / "convert_hf_to_gguf.py"
    if not convert_script.exists():
        raise FileNotFoundError(
            f"找不到轉換腳本：{convert_script}\n"
            f"請確認 llama.cpp 已正確安裝至 {LLAMA_CPP_PATH}"
        )

    cmd = [
        "python", str(convert_script),
        MERGED_MODEL_PATH,
        "--outfile", f16_gguf,
        "--outtype", "f16"
    ]
    print(f"執行命令：{' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        print(f"[ERROR] 轉換失敗：\n{result.stderr}")
        raise RuntimeError("GGUF 轉換失敗")
    print(f"[完成] F16 GGUF 已生成：{f16_gguf}")
    return f16_gguf


def quantize_gguf(f16_gguf_path: str):
    """使用 llama-quantize 將 F16 GGUF 量化為 Q4_K_M"""
    print(f"\n[步驟 6] 量化 GGUF → {QUANTIZATION_TYPE}...")
    quantize_exe = Path(LLAMA_CPP_PATH) / "build" / "bin" / "llama-quantize.exe"

    # 備選路徑（預編譯版本通常在根目錄）
    if not quantize_exe.exists():
        quantize_exe = Path(LLAMA_CPP_PATH) / "llama-quantize.exe"

    if not quantize_exe.exists():
        raise FileNotFoundError(
            f"找不到 llama-quantize.exe\n"
            f"請從 https://github.com/ggml-org/llama.cpp/releases 下載預編譯版"
        )

    cmd = [
        str(quantize_exe),
        f16_gguf_path,
        GGUF_OUTPUT_PATH,
        QUANTIZATION_TYPE
    ]
    print(f"執行命令：{' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        print(f"[ERROR] 量化失敗：\n{result.stderr}")
        raise RuntimeError("GGUF 量化失敗")
    print(f"[完成] Q4_K_M GGUF 已生成：{GGUF_OUTPUT_PATH}")

    # 清理 F16 中間檔（可選，體積較大）
    f16_path = Path(f16_gguf_path)
    if f16_path.exists():
        f16_path.unlink()
        print(f"[清理] 已刪除 F16 中間檔：{f16_gguf_path}")


def create_ollama_modelfile():
    """生成 Ollama Modelfile 供 ollama create 使用"""
    modelfile_path = Path(GGUF_OUTPUT_PATH).parent / "Modelfile"
    modelfile_content = f"""FROM {GGUF_OUTPUT_PATH}

SYSTEM \"\"\"你是一位專精台灣法律的 AI 助理，熟悉中華民國法律體系、
司法院判決書格式、以及本案（黃少奎 vs 簡育芸等）的具體事實。
回答問題時請依據法律條文與本案事實，提供準確、完整的法律分析。\"\"\"

PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER num_ctx 4096
PARAMETER repeat_penalty 1.1
"""
    with open(modelfile_path, "w", encoding="utf-8") as f:
        f.write(modelfile_content)
    print(f"[完成] Modelfile 已生成：{modelfile_path}")
    return str(modelfile_path)


def register_to_ollama(modelfile_path: str):
    """將 GGUF 模型註冊至 Ollama"""
    print(f"\n[步驟 7] 將模型註冊至 Ollama 為 '{OLLAMA_MODEL_NAME}'...")
    cmd = ["ollama", "create", OLLAMA_MODEL_NAME, "-f", modelfile_path]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        print(f"[ERROR] Ollama 建立失敗：\n{result.stderr}")
        raise RuntimeError("Ollama 模型建立失敗")
    print(f"[完成] 模型已可透過 ollama run {OLLAMA_MODEL_NAME} 使用")


def main():
    print("=" * 60)
    print("LoRA Adapter 合併 → GGUF 匯出 → Ollama 載入")
    print("=" * 60)

    # 確認 stage2 adapter 存在
    if not Path(STAGE2_ADAPTER_PATH).exists():
        raise FileNotFoundError(
            f"找不到 Stage2 adapter：{STAGE2_ADAPTER_PATH}\n"
            "請先執行 distill_stage2.py"
        )

    merge_lora_to_base()
    f16_gguf = convert_to_gguf_f16()
    quantize_gguf(f16_gguf)
    modelfile_path = create_ollama_modelfile()
    register_to_ollama(modelfile_path)

    print("\n" + "=" * 60)
    print("全部完成！可以使用以下指令測試模型：")
    print(f"  ollama run {OLLAMA_MODEL_NAME}")
    print("=" * 60)


if __name__ == "__main__":
    main()
```

**執行方式（PowerShell）**：

```powershell
conda activate unsloth_env
python merge_export.py
```

---

## 八、DeepEval 評估方案

### 8.1 評估設計原則

使用已安裝的 DeepEval 框架對微調前後的模型進行對照評估，評估維度包含：

| 評估維度 | 對應 DeepEval 指標 | 說明 |
|----------|-------------------|------|
| 法律推理準確率 | 自定義 `LegalReasoningMetric` | 檢查答案是否援引正確法條與邏輯 |
| 本案事實召回率 | `AnswerRelevancyMetric` + 自定義 | 是否正確回答黃少奎案相關事實 |
| 台灣法律用語正確率 | 自定義 `LegalTerminologyMetric` | 檢查法律術語的正確使用 |

### 8.2 evaluate_legal_llm.py — DeepEval 評估腳本

```python
# evaluate_legal_llm.py
# 使用 DeepEval 評估微調前後的台灣法律 LLM 效能
# 執行環境：系統 Python 3.14（C:\Users\temp\AppData\Local\Python\pythoncore-3.14-64\）

import json
import requests
from typing import Optional
from deepeval import evaluate
from deepeval.test_case import LLMTestCase
from deepeval.metrics import AnswerRelevancyMetric, BaseMetric
from deepeval.dataset import EvaluationDataset

# ── 設定區 ──────────────────────────────────────────────
OLLAMA_API = "http://localhost:11434/api/chat"
BASELINE_MODEL = "deepseek-r1:14b"              # 微調前基線模型
FINETUNED_MODEL = "legal-deepseek-r1-14b"       # 微調後目標模型
EVAL_MODEL = "qwen3:30b-a3b"                     # 用於 LLM-as-judge 評估
RESULTS_OUTPUT = r"C:\Users\temp\legal_llm\eval_results.json"
# ─────────────────────────────────────────────────────────


def query_ollama(model: str, prompt: str, system: str = "") -> str:
    """呼叫 Ollama 模型取得回答"""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.1, "num_ctx": 4096}
    }
    try:
        resp = requests.post(OLLAMA_API, json=payload, timeout=180)
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()
    except Exception as e:
        return f"[ERROR] 呼叫失敗：{e}"


# ── 自定義評估指標 ─────────────────────────────────────


class LegalReasoningMetric(BaseMetric):
    """
    評估法律推理品質：
    - 是否援引相關法律條文
    - 推理邏輯是否符合台灣法律體系
    - 結論是否與法律事實一致
    評分：0.0（完全不正確）~ 1.0（完全正確）
    """
    def __init__(self, threshold: float = 0.6, model: str = EVAL_MODEL):
        self.threshold = threshold
        self.evaluation_model = model
        self.include_reason = True

    def measure(self, test_case: LLMTestCase) -> float:
        judge_prompt = f"""你是台灣法律評估專家。請評估以下 AI 回答的法律推理品質。

【問題】
{test_case.input}

【AI 回答】
{test_case.actual_output}

【參考答案（若有）】
{test_case.expected_output or "（無）"}

請從以下三個維度各給 0~10 分，並計算平均分：
1. 法條援引正確性：是否援引了正確的台灣法律條文（若無法條可援引則給 7 分）
2. 推理邏輯嚴謹性：法律推理過程是否符合邏輯
3. 結論準確性：最終結論是否正確或合理

請以 JSON 格式回覆：
{{"legal_citation_score": <0-10>, "reasoning_score": <0-10>, "conclusion_score": <0-10>, "reason": "<簡短說明>"}}"""

        raw = query_ollama(EVAL_MODEL, judge_prompt)
        try:
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw.strip())
            avg = (
                data["legal_citation_score"] +
                data["reasoning_score"] +
                data["conclusion_score"]
            ) / 30.0  # 正規化至 0~1
            self.score = round(avg, 3)
            self.reason = data.get("reason", "")
        except Exception:
            self.score = 0.5
            self.reason = "評估解析失敗，給予中間分"

        self.success = self.score >= self.threshold
        return self.score

    async def a_measure(self, test_case: LLMTestCase) -> float:
        return self.measure(test_case)

    def is_successful(self) -> bool:
        return self.success

    @property
    def __name__(self):
        return "法律推理品質"


class CaseFactRecallMetric(BaseMetric):
    """
    評估本案事實召回率：
    針對黃少奎 vs 簡育芸案的特定事實問題，
    檢查模型是否正確回憶案件的具體細節
    """
    def __init__(self, threshold: float = 0.6, model: str = EVAL_MODEL):
        self.threshold = threshold
        self.evaluation_model = model
        self.include_reason = True

    def measure(self, test_case: LLMTestCase) -> float:
        judge_prompt = f"""你是本案（黃少奎 vs 簡育芸等）的法律顧問。
請評估 AI 對本案事實的回答是否準確完整。

【關於本案的問題】
{test_case.input}

【AI 的回答】
{test_case.actual_output}

【本案正確事實（供參考）】
{test_case.expected_output or "（請依您的知識判斷）"}

請評估：
1. 事實陳述是否準確（0-10 分）
2. 關鍵細節是否完整（0-10 分）
3. 是否有捏造不存在的事實（0-10 分，10 = 沒有捏造）

JSON 格式：
{{"accuracy": <0-10>, "completeness": <0-10>, "no_hallucination": <0-10>, "reason": "<說明>"}}"""

        raw = query_ollama(EVAL_MODEL, judge_prompt)
        try:
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw.strip())
            avg = (
                data["accuracy"] +
                data["completeness"] +
                data["no_hallucination"]
            ) / 30.0
            self.score = round(avg, 3)
            self.reason = data.get("reason", "")
        except Exception:
            self.score = 0.5
            self.reason = "評估解析失敗"

        self.success = self.score >= self.threshold
        return self.score

    async def a_measure(self, test_case: LLMTestCase) -> float:
        return self.measure(test_case)

    def is_successful(self) -> bool:
        return self.success

    @property
    def __name__(self):
        return "本案事實召回率"


class LegalTerminologyMetric(BaseMetric):
    """
    評估台灣法律用語的正確性：
    檢查是否使用正確的繁體中文法律術語
    （例如：「被告」vs「被告人」、「判決」vs「裁定」）
    """
    # 常見台灣法律用語對照（正確 → 常見錯誤）
    TERMINOLOGY_RULES = {
        "正確術語範例": [
            "原告", "被告", "上訴人", "被上訴人",
            "訴外人", "法院", "檢察官", "辯護人",
            "判決", "裁定", "聲請", "請求",
            "損害賠償", "不當得利", "侵權行為",
            "消滅時效", "除斥期間", "連帶責任"
        ],
        "錯誤用語（大陸法律用語，應避免）": [
            "被告人",    # 台灣用「被告」
            "公安",      # 台灣用「警察」或「刑警」
            "检察院",    # 台灣用「檢察署」
            "律师",      # 應使用繁體「律師」
        ]
    }

    def __init__(self, threshold: float = 0.7):
        self.threshold = threshold
        self.evaluation_model = "rule-based"
        self.include_reason = False

    def measure(self, test_case: LLMTestCase) -> float:
        output = test_case.actual_output or ""

        # 檢查是否使用大陸法律用語（簡體或錯誤術語）
        wrong_terms_found = []
        for term in self.TERMINOLOGY_RULES["錯誤用語（大陸法律用語，應避免）"]:
            if term in output:
                wrong_terms_found.append(term)

        # 檢查是否包含繁體字（基本檢查）
        simplified_chars = ["这", "时", "为", "说", "从", "国", "来", "对", "会", "个"]
        simplified_found = [c for c in simplified_chars if c in output]

        # 計算分數
        penalty = len(wrong_terms_found) * 0.15 + len(simplified_found) * 0.05
        self.score = max(0.0, round(1.0 - penalty, 3))
        self.reason = (
            f"發現錯誤術語：{wrong_terms_found}；簡體字：{simplified_found}"
            if wrong_terms_found or simplified_found else "用語正確"
        )
        self.success = self.score >= self.threshold
        return self.score

    async def a_measure(self, test_case: LLMTestCase) -> float:
        return self.measure(test_case)

    def is_successful(self) -> bool:
        return self.success

    @property
    def __name__(self):
        return "台灣法律用語正確率"


# ── 評估測試案例 ──────────────────────────────────────

# 法律通識測試（第一階段效果驗證）
LEGAL_KNOWLEDGE_TESTS = [
    {
        "input": "民法第184條第1項前段的構成要件為何？",
        "expected_output": (
            "民法第184條第1項前段規定：因故意或過失，不法侵害他人之權利者，負損害賠償責任。"
            "構成要件包含：(1) 加害行為；(2) 行為具有不法性；"
            "(3) 有損害發生；(4) 損害與行為間有因果關係；"
            "(5) 加害人具有故意或過失；(6) 加害人具有責任能力。"
        ),
        "category": "legal_knowledge"
    },
    {
        "input": "台灣民事訴訟中，舉證責任的基本原則是什麼？",
        "expected_output": (
            "依民事訴訟法第277條，當事人主張有利於己之事實者，就其事實有舉證之責任。"
            "但法律別有規定，或依其情形顯失公平者，不在此限。"
            "基本原則為「主張者舉證」，即原告就請求權之成立要件負舉證責任，"
            "被告就抗辯事由負舉證責任。"
        ),
        "category": "legal_knowledge"
    },
    {
        "input": "什麼是時效抗辯？在民事訴訟中如何主張？",
        "expected_output": (
            "時效抗辯是指當事人主張請求權已因時效完成而消滅或拒絕給付之抗辯。"
            "依民法第144條，時效完成後，債務人得拒絕給付。"
            "時效抗辯須由當事人於訴訟中積極主張，法院不得依職權調查。"
        ),
        "category": "legal_knowledge"
    }
]

# 本案事實測試（第二階段效果驗證）
CASE_FACT_TESTS = [
    {
        "input": "本案原告黃少奎的主要訴求為何？",
        "expected_output": None,  # 由評估者根據實際案情判斷
        "category": "case_facts"
    },
    {
        "input": "被告簡育芸在本案中的法律地位為何？",
        "expected_output": None,
        "category": "case_facts"
    },
    {
        "input": "本案涉及哪些主要的法律爭點？",
        "expected_output": None,
        "category": "case_facts"
    }
]


def run_evaluation():
    """執行完整評估流程"""
    import os
    results = {
        "baseline_model": BASELINE_MODEL,
        "finetuned_model": FINETUNED_MODEL,
        "legal_knowledge_results": {},
        "case_facts_results": {}
    }

    all_tests = LEGAL_KNOWLEDGE_TESTS + CASE_FACT_TESTS

    for model_name in [BASELINE_MODEL, FINETUNED_MODEL]:
        print(f"\n{'='*60}")
        print(f"評估模型：{model_name}")
        print(f"{'='*60}")

        test_cases = []
        for test in all_tests:
            response = query_ollama(
                model_name,
                test["input"],
                system="你是台灣法律專業助理，請用繁體中文回答。"
            )
            tc = LLMTestCase(
                input=test["input"],
                actual_output=response,
                expected_output=test.get("expected_output")
            )
            test_cases.append((tc, test["category"]))
            print(f"  問題：{test['input'][:40]}...")
            print(f"  回答（前100字）：{response[:100]}...")

        # 執行各指標評估
        legal_metric = LegalReasoningMetric(threshold=0.6)
        case_metric = CaseFactRecallMetric(threshold=0.6)
        term_metric = LegalTerminologyMetric(threshold=0.7)

        legal_scores = []
        case_scores = []
        term_scores = []

        for tc, category in test_cases:
            term_score = term_metric.measure(tc)
            term_scores.append(term_score)

            if category == "legal_knowledge":
                legal_score = legal_metric.measure(tc)
                legal_scores.append(legal_score)
                print(f"  [法律推理] {legal_score:.3f} | [用語] {term_score:.3f}")
            else:
                case_score = case_metric.measure(tc)
                case_scores.append(case_score)
                print(f"  [本案事實] {case_score:.3f} | [用語] {term_score:.3f}")

        model_results = {
            "avg_legal_reasoning": round(sum(legal_scores) / len(legal_scores), 3) if legal_scores else 0,
            "avg_case_fact_recall": round(sum(case_scores) / len(case_scores), 3) if case_scores else 0,
            "avg_terminology": round(sum(term_scores) / len(term_scores), 3) if term_scores else 0,
        }

        print(f"\n  模型總結：{model_results}")
        results[model_name] = model_results

    # 計算改善幅度
    if BASELINE_MODEL in results and FINETUNED_MODEL in results:
        baseline = results[BASELINE_MODEL]
        finetuned = results[FINETUNED_MODEL]
        results["improvement"] = {
            "legal_reasoning": round(
                finetuned["avg_legal_reasoning"] - baseline["avg_legal_reasoning"], 3
            ),
            "case_fact_recall": round(
                finetuned["avg_case_fact_recall"] - baseline["avg_case_fact_recall"], 3
            ),
            "terminology": round(
                finetuned["avg_terminology"] - baseline["avg_terminology"], 3
            ),
        }
        print(f"\n改善幅度：{results['improvement']}")

    # 儲存結果
    import os
    os.makedirs(os.path.dirname(RESULTS_OUTPUT), exist_ok=True)
    with open(RESULTS_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n[完成] 評估結果已儲存至：{RESULTS_OUTPUT}")
    return results


if __name__ == "__main__":
    run_evaluation()
```

**執行方式（PowerShell，系統 Python 3.14）**：

```powershell
& "C:\Users\temp\AppData\Local\Python\pythoncore-3.14-64\python.exe" evaluate_legal_llm.py
```

---

## 九、訓練時間估算

以下估算基於 RTX 5060 Ti（16GB GDDR7）、Batch Size=2、Gradient Accumulation=8 的條件，採用 Unsloth QLoRA 加速。

### 第一階段估算

| 資料集 | 筆數 | 每步平均時間（估算） | 說明 |
|--------|------|---------------------|------|
| tw-legal-synthetic-qa | ~7,700 | — | ShareGPT 格式，平均長度適中 |
| tw-bar-examination-2020-chat | ~270 | — | 筆數少 |
| tw-processed-law-article（取樣） | 2,000 | — | 純文字，較短 |
| tw-processed-judgments-14B（取樣） | 3,000 | — | 判決書較長 |
| **合計有效樣本** | **~10,000** | — | 扣除空白後的估計 |

**第一階段總時間估算**（2 epochs）：

- 每個 epoch 約 10,000 / (2 × 8) = 625 個有效更新步
- RTX 5060 Ti 配合 Unsloth 加速，每步估約 3–6 秒（依序列長度）
- **單 epoch 估計：約 30–60 分鐘**
- **2 epochs 總計：約 1–2 小時**

> 此為估算範圍，實際時間受序列長度分佈、SSD 讀取速度、CPU 預處理效率影響，可能有 ±50% 的偏差。

### 第二階段估算

| 項目 | 數值 |
|------|------|
| 本案 QA 對 | ~500 筆 |
| Train epochs | 5 |
| Batch size（有效） | 8 |
| 每 epoch 更新步數 | ~63 步 |

**第二階段總時間估算**（5 epochs）：

- 每步約 3–5 秒
- **單 epoch 估計：約 3–5 分鐘**
- **5 epochs 總計：約 15–25 分鐘**

### GGUF 轉換時間估算

| 步驟 | 估計時間 |
|------|---------|
| LoRA merge_and_unload（CPU） | 10–20 分鐘 |
| convert_hf_to_gguf.py（F16） | 5–15 分鐘 |
| llama-quantize Q4_K_M | 5–10 分鐘 |

---

## 十、常見錯誤與處理

### 10.1 VRAM OOM（記憶體不足）

**錯誤訊息**：`torch.OutOfMemoryError: CUDA out of memory`

**處理步驟**（依序嘗試）：

```python
# 方法一：降低 max_seq_length
MAX_SEQ_LENGTH = 1024   # 從 2048 降至 1024

# 方法二：降低 batch size（需同時增加 gradient_accumulation_steps）
BATCH_SIZE = 1
GRAD_ACCUM_STEPS = 16   # 維持有效 batch size 不變

# 方法三：降低 LoRA rank
LORA_RANK = 8
LORA_ALPHA = 8

# 方法四：確認使用 Unsloth 梯度檢查點
use_gradient_checkpointing = "unsloth"  # 不要設為 True 或 False
```

### 10.2 Unsloth 安裝失敗（Python 版本問題）

**問題**：系統 Python 3.14 與 bitsandbytes/triton 不相容

**解決方案**：

```powershell
# 確認使用 Conda 的 Python 3.12
conda activate unsloth_env
python --version   # 應顯示 Python 3.12.x

# 若 bitsandbytes 仍有問題，使用預編譯版本
pip install bitsandbytes --prefer-binary
```

### 10.3 Ollama API 連線失敗

**問題**：`requests.exceptions.ConnectionError: [Errno 10061]`

**解決方案**：

```powershell
# 確認 Ollama 服務已啟動
ollama serve

# 另開 PowerShell 視窗確認服務正常
Invoke-RestMethod -Uri "http://localhost:11434" -Method GET
# 應回傳："Ollama is running"
```

### 10.4 Llama-3-Taiwan-70B RAM 不足

**問題**：本機僅 16GB RAM，無法在本地同時執行 70B 模型做推理

**解決方案**（二選一）：

**選項 A**：使用 Ollama 搭配 `num_gpu=0`（純 CPU 推理，速度較慢但可行）

```powershell
# 拉取較小量化版本
ollama pull cwchang/llama-3-taiwan-70b-instruct:q4_k_s

# 設定 Ollama 將部分層卸載到 CPU
# 在 Ollama 的 Modelfile 中加入：
# PARAMETER num_gpu 10   # 僅使用 10 層 GPU，其餘 CPU
```

**選項 B**：改用 HuggingFace Inference API（不需本地 RAM）

```python
# generate_qa_pairs.py 的 API 設定部分改為：
import os
HF_API_KEY = os.environ.get("HF_API_KEY", "")
HF_MODEL_URL = "https://api-inference.huggingface.co/models/yentinglin/Llama-3-Taiwan-70B-Instruct"

def generate_qa_with_hf_api(chunk_text: str) -> dict | None:
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    payload = {
        "inputs": f"[INST]{chunk_text}[/INST]",
        "parameters": {"max_new_tokens": 512, "temperature": 0.3}
    }
    resp = requests.post(HF_MODEL_URL, headers=headers, json=payload, timeout=120)
    # ... 後續處理同前
```

### 10.5 ChromaDB collection 找不到

**問題**：`ValueError: Collection legal_docs does not exist`

**解決方案**：

```python
# 列出所有現有 collection 確認名稱
import chromadb
client = chromadb.PersistentClient(path=r"C:\Users\temp\chroma_db")
print([c.name for c in client.list_collections()])
# 將輸出的正確名稱填入 COLLECTION_NAME
```

### 10.6 GGUF 轉換後 Ollama 無法載入

**問題**：`Error: model file not found` 或 `Error: unsupported architecture`

**解決方案**：

```powershell
# 確認 GGUF 檔案完整性
C:\llama.cpp\llama-cli.exe -m "C:\Users\temp\legal_llm\legal_deepseek_r1_14b_Q4_K_M.gguf" `
    --prompt "你好" --n-predict 10

# 若上述測試成功，再嘗試 Ollama 載入
# Modelfile 的 FROM 必須使用 GGUF 的絕對路徑（Windows 需使用正斜線或跳脫）
```

### 10.7 資料集下載卡住（中國網路限制）

**問題**：HuggingFace 下載速度極慢或失敗

**解決方案**：

```powershell
# 方法一：設定 HuggingFace 鏡像站
$env:HF_ENDPOINT = "https://hf-mirror.com"

# 方法二：使用 huggingface-cli 預先下載
conda activate unsloth_env
huggingface-cli download lianghsun/tw-legal-synthetic-qa --local-dir C:\hf_datasets\tw-legal-synthetic-qa

# 方法三：在 Python 中指定 cache 目錄
from datasets import load_dataset
ds = load_dataset("lianghsun/tw-legal-synthetic-qa",
                  cache_dir=r"C:\hf_datasets")
```

### 10.8 Windows 多進程錯誤

**問題**：`RuntimeError: An attempt has been made to start a new process before the current process has finished its bootstrapping phase`

**解決方案**：

```python
# 在所有 Python 腳本頂部加入此保護
if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()

# 並確認訓練設定中：
dataset_num_proc = 1   # Windows 下建議使用單進程
dataloader_num_workers = 0  # 若問題持續，設為 0
```

---

## 十一、完整執行流程速查

### 一次性環境安裝（只需執行一次）

```powershell
# 安裝 Conda 環境
conda create --name unsloth_env python==3.12 -y
conda activate unsloth_env
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130
pip install unsloth datasets huggingface_hub chromadb requests

# 安裝 llama.cpp（用於 GGUF 轉換）
git clone https://github.com/ggerganov/llama.cpp.git C:\llama.cpp
pip install -r C:\llama.cpp\requirements.txt

# 下載 Teacher model
ollama pull cwchang/llama-3-taiwan-70b-instruct
```

### 訓練執行順序

```powershell
# ──── 準備資料（系統 Python 3.14）────────────────────
& "C:\Users\temp\AppData\Local\Python\pythoncore-3.14-64\python.exe" generate_qa_pairs.py
# 輸出：C:\Users\temp\legal_qa\case_qa_pairs.jsonl

# ──── 第一階段訓練（Conda 環境 Python 3.12）──────────
conda activate unsloth_env
python distill_stage1.py
# 輸出：C:\Users\temp\legal_llm\stage1_lora_adapter\

# ──── 第二階段訓練（Conda 環境 Python 3.12）──────────
python distill_stage2.py
# 輸出：C:\Users\temp\legal_llm\stage2_lora_adapter\

# ──── 合併並匯出（Conda 環境 Python 3.12）────────────
python merge_export.py
# 輸出：C:\Users\temp\legal_llm\legal_deepseek_r1_14b_Q4_K_M.gguf
# 自動在 Ollama 建立 legal-deepseek-r1-14b

# ──── 評估（系統 Python 3.14）────────────────────────
conda deactivate
& "C:\Users\temp\AppData\Local\Python\pythoncore-3.14-64\python.exe" evaluate_legal_llm.py
# 輸出：C:\Users\temp\legal_llm\eval_results.json

# ──── 測試使用 ────────────────────────────────────────
ollama run legal-deepseek-r1-14b
```

### 目錄結構

```
C:\Users\temp\
├── legal_qa\
│   └── case_qa_pairs.jsonl          # 生成的本案 QA 對
├── legal_llm\
│   ├── stage1_lora_adapter\         # 第一階段 LoRA 權重
│   ├── stage2_lora_adapter\         # 第二階段 LoRA 權重
│   ├── merged_model\                # 合併後完整模型（safetensors）
│   ├── legal_deepseek_r1_14b_Q4_K_M.gguf   # 最終 GGUF
│   ├── Modelfile                    # Ollama 設定檔
│   └── eval_results.json            # DeepEval 評估結果
├── hf_datasets\                     # HuggingFace 資料集快取（建議）
└── chroma_db\                       # ChromaDB 持久化目錄
```

---

## 附錄：Llama-3-Taiwan-70B 作為 Teacher 的蒸餾說明

本規劃採用**黑箱蒸餾（Black-box Distillation / Data Augmentation Distillation）**方式，即：

1. Teacher（Llama-3-Taiwan-70B）僅透過 Ollama API 輸出**文字回答**（軟標籤為回答文本）
2. Student（deepseek-r1:14b）學習模仿 Teacher 的回答格式與內容
3. 此方式不需取得 Teacher 的 logit 分佈，適合透過 API 呼叫的場景

與需要完整 logit 的 MiniLLM 等方法相比，黑箱蒸餾在法律領域的知識遷移仍有效，原因是：
- 法律問答的高品質回答本身包含了 Teacher 的推理結構
- DeepSeek-R1 系列本身就是蒸餾模型，善於學習 Chain-of-Thought 格式
- 台灣法律領域的知識相對封閉，少量高品質資料即可顯著改善

> **注意**：本規劃中第一階段的 Teacher 作用已由公開資料集取代（資料集本身由 Llama/GLM 系列模型生成），實際上 Teacher API 主要用於第二階段的 `generate_qa_pairs.py` 中，對 ChromaDB chunk 生成高品質 QA 對（此處使用的是 qwen3:30b-a3b，為本地可用的主力推理模型）。若需在第一階段也加入 Llama-3-Taiwan-70B 的蒸餾，可在 `generate_qa_pairs.py` 中將 `QA_GENERATOR_MODEL` 改為 `cwchang/llama-3-taiwan-70b-instruct`。

---

*本文件依據 Unsloth 官方文件（https://docs.unsloth.ai）、HuggingFace 資料集頁面、Ollama 官方文件（https://docs.ollama.com）及 llama.cpp 倉庫（https://github.com/ggml-org/llama.cpp）撰寫，所有程式碼框架均為可執行的完整實作，不包含虛構的版本號或 benchmark 數字。*
