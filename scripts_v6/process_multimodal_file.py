# ==============================================================================
# [CRITICAL DEPENDENCY WARNING] Group 2: 核心加工管線 (Core Pipeline)
# ------------------------------------------------------------------------------
# ⚠️ 此檔案屬於高度解耦架構的【Group 2】。
# 修改此檔案時，必須確保多執行緒併發 (Concurrency) 及跨進程 JSON 狀態寫入的安全。
# 任何資料輸出格式的變動，都會直接導致 Group 5 (UI) 與 Group 8 (KPI) 癱瘓！
# 修改前請務必參閱：PIPELINE_DEPENDENCIES.md
# ==============================================================================
import sys
import argparse
from pathlib import Path

# Add current folder to sys.path
sys.path.append(str(Path(__file__).resolve().parent))

try:
    from multimodal_input import MultimodalLegalInput
except ImportError:
    # Fallback to local import if called from workspace
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from multimodal_input import MultimodalLegalInput

def main():
    # Force output encoding to UTF-8 to prevent CP950 coding issues in Windows console
    if sys.platform == "win32":
        try:
            import io
            if hasattr(sys.stdout, 'buffer'):
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="CLI to process local file with Whisper ASR or Tesseract OCR")
    parser.add_argument("--path", required=False, help="Absolute file path on disk")
    parser.add_argument("--type", required=False, help="File extension type (e.g. mp4, pdf)")
    parser.add_argument("--gpu-id", type=int, default=0, help="Target GPU index (e.g. 0 or 1)")
    args = parser.parse_args()

    import os
    env_path = os.environ.get("PARSE_FILE_PATH")
    env_type = os.environ.get("PARSE_FILE_TYPE")
    env_gpu_id = os.environ.get("PARSE_GPU_ID")

    if env_path and env_type:
        file_path = Path(env_path)
        ext = env_type.lower()
        gpu_id = int(env_gpu_id) if env_gpu_id else 0
    else:
        if not args.path or not args.type:
            print("❌ [錯誤] 缺少必要的 --path 或 --type 參數，且未偵測到環境變數輸入。")
            sys.exit(1)
        file_path = Path(args.path)
        ext = args.type.lower()
        gpu_id = args.gpu_id

    if not file_path.exists():
        print(f"❌ [錯誤] 本機檔案不存在: {file_path}")
        sys.exit(1)

    # Automated testing simulation: sleep to test timeout
    if "lexmind_sparse_test" in file_path.name:
        import time
        time.sleep(10)
        sys.exit(0)

    try:
        processor = MultimodalLegalInput(model_size='small', gpu_id=gpu_id)
        
        if ext in ['mp4', 'mp3', 'wav']:
            # Run Whisper ASR (on GPU if available, otherwise CPU)
            result = processor.transcribe_audio(file_path)
            print(result)
        elif ext in ['pdf', 'png', 'jpg', 'jpeg']:
            # Run OCR
            full_text = processor.ocr_document(file_path)
            if full_text.startswith("❌") or full_text.startswith("[ERROR]"):
                raise RuntimeError(full_text)
            print(full_text)
        else:
            # Plain text read
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                print(f.read())
    except Exception as e:
        print(f"❌ [錯誤] 執行 Python 處理失敗: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

