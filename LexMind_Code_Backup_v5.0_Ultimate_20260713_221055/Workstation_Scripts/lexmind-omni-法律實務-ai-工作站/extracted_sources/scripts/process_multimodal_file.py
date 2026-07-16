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
    parser.add_argument("--path", required=True, help="Absolute file path on disk")
    parser.add_argument("--type", required=True, help="File extension type (e.g. mp4, pdf)")
    parser.add_argument("--gpu-id", type=int, default=0, help="Target GPU index (e.g. 0 or 1)")
    args = parser.parse_args()

    file_path = Path(args.path)
    ext = args.type.lower()

    if not file_path.exists():
        print(f"❌ [錯誤] 本機檔案不存在: {args.path}")
        sys.exit(1)

    try:
        processor = MultimodalLegalInput(model_size='small', gpu_id=args.gpu_id)
        
        if ext in ['mp4', 'mp3', 'wav']:
            # Run Whisper ASR (on GPU if available, otherwise CPU)
            result = processor.transcribe_audio(file_path)
            print(result)
        elif ext in ['pdf', 'png', 'jpg', 'jpeg']:
            # Run OCR
            full_text = processor.ocr_document(file_path)
            if full_text.startswith("❌"):
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
