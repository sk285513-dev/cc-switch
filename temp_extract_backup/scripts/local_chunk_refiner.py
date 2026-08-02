import os
import sys
import glob
import re
import argparse
import subprocess
from pathlib import Path

# 載入本地路由
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from ollama_router import OllamaRouter

def clean_deepseek_output(text):
    # 清除推理模型特有的思考過程 <think>...</think>
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

def process_chunk(chunk_path, router, model):
    print(f"\n[Local Refiner] 正在處理切片: {os.path.basename(chunk_path)}")
    with open(chunk_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()

    # 1. 物理隔離：抽離時間戳記並打上 Line ID
    lines = content.split('\n')
    mapping = {}
    indexed_input = ""
    
    for i, line in enumerate(lines):
        match = re.match(r'^(\[\d{2}:\d{2}(?::\d{2})?\]\s*)(.*)', line)
        if match:
            mapping[i] = match.group(1)
            indexed_input += f"Line {i}: {match.group(2)}\n"
        else:
            mapping[i] = ""
            indexed_input += f"Line {i}: {line}\n"

    system_prompt = (
        "這是一份由雲端大模型初步產出的法律課程錄音內容文字稿成品。\n"
        "為幫助理解並限制你胡說八道，請先讀懂上下文。\n\n"
        "你的唯一任務是進行文字內容的「校正與清洗」：\n"
        "1. 徹底刪除所有的口語贅字（如「那個」、「然後」、「就是說」、「嗯」、「啊」）。\n"
        "2. 修復同音錯字（如將「格論」修正為「各論」、「地政治」修正為「地政士」）。\n\n"
        "【嚴格輸出格式】：\n"
        "輸入文本帶有 'Line X:' 標籤，你必須『原封不動』地保留每一個 'Line X:' 標籤，並在冒號後輸出清洗後的文字！\n"
        "你【絕對禁止】合併行數、新增或刪除任何一行！你回傳的行數必須和輸入完全一樣！\n"
        "如果某行本來就是廢話，即使清洗後變為空白，你也必須輸出 'Line X: '。"
    )

    prompt = f"請嚴格依據 'Line X:' 格式逐行校對以下文稿：\n\n{indexed_input}"

    try:
        response = router.generate_chat(prompt, system_prompt=system_prompt, model=model, stream=False)
        cleaned_response = clean_deepseek_output(response)
        
        # 2. 完美還原：將回傳的 Line X 對應回原始的時間戳記
        restored_lines = []
        parsed_lines = {}
        for out_line in cleaned_response.split('\n'):
            out_match = re.match(r'^Line\s+(\d+):\s*(.*)', out_line.strip(), re.IGNORECASE)
            if out_match:
                idx = int(out_match.group(1))
                parsed_lines[idx] = out_match.group(2)
                
        # 依照原本的行數重建，如果有遺漏則用原文字兜底
        for i in range(len(lines)):
            original_timestamp = mapping[i]
            if i in parsed_lines:
                restored_lines.append(f"{original_timestamp}{parsed_lines[i]}")
            else:
                # Fallback to original line if LLM skipped it
                restored_lines.append(lines[i])
                
        final_text = '\n'.join(restored_lines)
        
        with open(chunk_path, 'w', encoding='utf-8') as f:
            f.write(final_text)
        print(f"  -> 完成清洗並已覆寫 (行數對齊完美率: {len(parsed_lines)}/{len(lines)}): {os.path.basename(chunk_path)}")
    except Exception as e:
        print(f"  -> [錯誤] 處理 {os.path.basename(chunk_path)} 時發生例外: {str(e)}")

def refine_task(task_id, model="deepseek-r1:32b"):
    # 在備份區找尋任務資料夾
    backup_dirs = [Path("F:/chunks_backup"), Path("E:/chunks_backup"), Path("A:/chunks")]
    task_dir = None
    
    for base in backup_dirs:
        target = base / task_id
        if target.exists() and target.is_dir():
            task_dir = target
            break
            
    if not task_dir:
        print(f"找不到任務 {task_id} 的備份資料夾！")
        return False
        
    print(f"找到任務目錄: {task_dir}")
    
    # 尋找所有 chunk_XXX_*.txt
    search_pattern = str(task_dir / "chunk_*_*.txt")
    chunk_files = sorted(glob.glob(search_pattern))
    
    if not chunk_files:
        print(f"目錄中沒有找到任何 chunk 文字檔！")
        return False
        
    print(f"共找到 {len(chunk_files)} 個切片檔案。")
    # 我們需要將它當作原本的管線執行，但 merge_transcript 期望從 A:\chunks 讀取。
    # 為了保護原始備份，我們將檔案複製到 A:\chunks 中進行處理。
    a_chunks_dir = Path("A:/chunks") / task_id
    print(f"從 {task_dir} 複製檔案到 {a_chunks_dir} 進行處理，以保護原始備份...")
    if task_dir != a_chunks_dir:
        os.makedirs(a_chunks_dir, exist_ok=True)
        import shutil
        for item in os.listdir(task_dir):
            src = task_dir / item
            dst = a_chunks_dir / item
            if src.is_file():
                shutil.copy2(src, dst)

    router = OllamaRouter(default_model=model)
    
    for chunk_file in chunk_files:
        # 目標處理路徑 (A:\chunks)
        target_chunk_file = a_chunks_dir / os.path.basename(chunk_file)
        process_chunk(str(target_chunk_file), router, model)
        
    print("\n[Local Refiner] 所有切片清洗完成。正在呼叫後續合併程序...")
    try:
        print(">> 執行 merge_transcript.py...")
        subprocess.run([sys.executable, "scripts/merge_transcript.py", "--task-id", task_id], cwd="C:/LocalAI_Workstation", check=True)
        
        print(">> 執行 markdown_formatter.py...")
        subprocess.run([sys.executable, "scripts/markdown_formatter.py", "--task-id", task_id], cwd="C:/LocalAI_Workstation", check=True)
        
        print(f"\n✅ 任務 {task_id} 本地重煉管線執行完畢！最終成品已輸出。")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 執行後續管線時失敗: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="本地端模型二次清洗管線")
    parser.add_argument("--task_id", type=str, required=True, help="任務 ID (例如 task_20260725_205244_9848)")
    parser.add_argument("--model", type=str, default="deepseek-r1:32b", help="本地模型名稱")
    
    args = parser.parse_args()
    refine_task(args.task_id, args.model)
