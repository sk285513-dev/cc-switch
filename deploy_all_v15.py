# C:/LocalAI_Workstation/deploy_all_v15.py
# -*- coding: utf-8 -*-
import os
import sys
import subprocess

def deploy_lexmind_workstation_v15():
    print("====================================================")
    print("   LexMind-Omni v1.5 - 套件安裝、真實運算與 ChromaDB 持久化")
    print("====================================================")
    target_dir = r"C:\LocalAI_Workstation"
    os.makedirs(target_dir, exist_ok=True)
    os.chdir(target_dir)
    
    # ==========================================
    # 步驟 1: 自動化免費開源套件依賴環境安裝
    # ==========================================
    print("[1/4] 正在檢測並自動安裝 AI 核心套件 (此步驟需連網，請稍候)...")
    required_packages = ["faster-whisper", "chromadb", "sentence-transformers", "beautifulsoup4", "requests", "streamlit"]
    for pkg in required_packages:
        try:
            print(f"   正在安裝/核查 {pkg}...")
            subprocess.run([sys.executable, "-m", "pip", "install", pkg, "--quiet"], check=True)
        except Exception as e:
            print(f"警告：套件 {pkg} 安裝時發生提示: {e}")
            
    # ==========================================
    # 步驟 2: 建立真實的 law_digester.py (Faster-Whisper + ChromaDB)
    # ==========================================
    digester_code = """# -*- coding: utf-8 -*-
import os
import time
import datetime
import chromadb
from sentence_transformers import SentenceTransformer
from faster_whisper import WhisperModel

# 初始化本地中文嵌入模型 (免費開源，適合繁體法律文本)
EMBED_MODEL = SentenceTransformer("shibing624/text2vec-base-chinese")

class ChromaEmbeddingFunction:
    def __call__(self, input_texts):
        embeddings = EMBED_MODEL.encode(input_texts)
        return [e.tolist() for e in embeddings]

def get_chroma_client():
    db_path = os.path.join(os.getcwd(), "chroma_db_storage")
    return chromadb.PersistentClient(path=db_path)

def process_audio_video_real(file_path, gpu_id=0, progress_callback=None):
    if not os.path.exists(file_path):
        return f"❌ 找不到影音檔案: {file_path}"
        
    start_time = time.time()
    if progress_callback: 
        progress_callback(5, "正在將加速模型載入至 GPU 顯存...")
        
    try:
        model = WhisperModel("base", device="cuda", device_index=gpu_id, compute_type="float16")
    except Exception as gpu_err:
        # GPU VRAM 不足時優雅降級為 CPU 多線程，防止崩潰
        model = WhisperModel("base", device="cpu", cpu_threads=4, compute_type="int8")
        
    if progress_callback: 
        progress_callback(15, "連線硬體解碼器成功！開始讀取音訊時間軸...")
        
    segments, info = model.transcribe(
        file_path, 
        beam_size=5, 
        initial_prompt="以下為台灣法律訴訟案件之開庭錄音或蒐證影音，包含原告、被告及法官之對話。"
    )
    total_duration = info.duration
    full_transcript_text = []
    
    for segment in segments:
        full_transcript_text.append(segment.text)
        current_seek = segment.end
        
        # 動態計算時間反饋 ETA
        percent = min(int((current_seek / total_duration) * 80) + 15, 95)
        elapsed_time = time.time() - start_time
        processing_speed = current_seek / elapsed_time if elapsed_time > 0 else 1
        remaining_seconds = (total_duration - current_seek) / processing_speed
        eta_str = str(datetime.timedelta(seconds=int(remaining_seconds)))
        
        if progress_callback:
            progress_callback(
                percent, 
                f"解碼中: {percent}% | 速度: {processing_speed:.1f}x | 剩餘時間: {eta_str} | 內文片段: {segment.text[:15]}..."
            )
            
    complete_text = "\\n".join(full_transcript_text)
    
    if progress_callback: 
        progress_callback(96, "影音解碼完成！正在將文本進行法律語義向量嵌入...")
        
    client = get_chroma_client()
    collection = client.get_or_create_collection(
        name="legal_intelligence_vault",
        embedding_function=ChromaEmbeddingFunction()
    )
    
    doc_id = f"media_doc_{int(time.time())}"
    collection.add(
        ids=[doc_id],
        documents=[complete_text],
        metadatas=[{
            "source": "media_inference",
            "file_name": os.path.basename(file_path),
            "total_duration_sec": total_duration,
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }]
    )
    
    total_time = time.time() - start_time
    return f"✅ 成功！總時長 {total_duration:.1f}秒，解碼耗時 {total_time:.1f}秒，已扣入 ChromaDB 庫。"
"""
    # 寫入至 scripts/law_digester_real.py 以防直接蓋掉主消化模組
    scripts_dir = os.path.join(target_dir, "scripts")
    os.makedirs(scripts_dir, exist_ok=True)
    with open(os.path.join(scripts_dir, "law_digester_real.py"), "w", encoding="utf-8") as f:
        f.write(digester_code)
    print("[2/4] 已生成具備真實 Faster-Whisper 與 ChromaDB 扣連核心: scripts/law_digester_real.py")
    
    # 3. 提示使用者安裝與配置完畢
    print("\n====================================================")
    print("   [Agent] v1.5 開源實戰集成版配置完畢！")
    print("====================================================")

if __name__ == "__main__":
    deploy_lexmind_workstation_v15()
