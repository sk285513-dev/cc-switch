import os
import re
import sys
import glob

# Ensure we can import OllamaRouter
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from ollama_router import OllamaRouter

def clean_deepseek_output(text):
    # Remove <think>...</think> blocks from deepseek responses
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

def chunk_text(text, max_chars=2000):
    # Simple chunking by paragraph or length
    chunks = []
    paragraphs = text.split('\n')
    current_chunk = ""
    
    for p in paragraphs:
        if len(current_chunk) + len(p) > max_chars and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = p + "\n"
        else:
            current_chunk += p + "\n"
            
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    return chunks

def refine_file(filepath, model="deepseek-r1:32b"):
    router = OllamaRouter(default_model=model)
    
    print(f"Refining: {filepath}")
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        content = f.read()
        
    chunks = chunk_text(content, max_chars=2000)
    print(f"Total chunks: {len(chunks)}")
    
    refined_chunks = []
    system_prompt = (
        "你是一個專業的法律實務文字校對助理。你的任務是進行以下三項工作：\n"
        "1. 徹底刪除所有的口語贅字（如'那個'、'然後'、'就是說'、'嗯'、'啊'）。\n"
        "2. 修復並刪除任何無限重複跳針的段落。\n"
        "3. 確保不出現非法的同音錯字（絕對不可出現'地政治'、'消滅實效'、'格論'、'遞贈式'）。\n"
        "請直接輸出修正後的文字，保持原有的段落與語意。除了修正後的文字外，絕對不要輸出任何其他解釋、引言或問候語。"
    )
    
    for i, chunk in enumerate(chunks):
        print(f"Processing chunk {i+1}/{len(chunks)}...")
        prompt = f"請校對以下文稿：\n\n{chunk}"
        try:
            # We don't stream here to avoid messy console output, we just wait for the result
            response = router.generate_chat(prompt, system_prompt=system_prompt, model=model, stream=False)
            cleaned = clean_deepseek_output(response)
            refined_chunks.append(cleaned)
        except Exception as e:
            print(f"Error on chunk {i+1}: {e}")
            return False
            
    # Reassemble
    refined_text = "\n".join(refined_chunks)
    
    # Write back
    with open(filepath, 'w', encoding='utf-8-sig') as f:
        f.write(refined_text)
        
    print(f"Successfully refined {filepath}")
    return True

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', type=str, help='Test a specific filename (e.g. [民法_ch2])')
    args = parser.parse_args()
    
    processed_dir = r"A:\processed_md"
    
    if args.test:
        files = [os.path.join(processed_dir, f) for f in os.listdir(processed_dir) if args.test in f and f.endswith('.txt')]
        if not files:
            print("Test file not found.")
        else:
            refine_file(files[0])
    else:
        print("Batch mode not fully implemented yet. Please use --test to test single files.")
