import os
import sys
from pathlib import Path

# Setup paths
workspace_root = "C:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站"
sys.path.append(os.path.join(workspace_root, "scripts_v6"))

from auto_ingest_bot import is_file_content_legal, SUPPORTED_EXTS
from file_watcher import SUPPORTED_EXTENSIONS

test_dir = os.path.join(workspace_root, "sandbox_test_blacklist")
os.makedirs(test_dir, exist_ok=True)

# Mock files
mock_files = [
    "民法_第01講.mp4",                            # Valid
    "chunk_001_民事訴訟法_第01講.wav",            # Blacklist (chunk_)
    "temp_audio_行政法_總複習.mp4",               # Blacklist (temp_)
    "行政法_總複習_逐字稿.txt",                   # Blacklist (逐字稿) and unsupported by watcher
    "民事訴訟法_第01講_chunks.json"               # Unsupported extension
]

print("=== 1. 建立遞迴災難與殘留檔案沙盒環境 ===")
for f in mock_files:
    path = os.path.join(test_dir, f)
    with open(path, 'w', encoding='utf-8') as file:
        file.write("包含法律關鍵字的假內容，例如民法第197條。")
    print(f"建立測試檔案: {f}")

print("\n=== 2. auto_ingest_bot.py 防護測試 (來源審查) ===")
for f in mock_files:
    path = os.path.join(test_dir, f)
    ext = os.path.splitext(f)[1].lower()
    
    # Simulate auto_ingest_bot extension check
    if ext not in {'.png', '.jpg', '.jpeg', '.mp3', '.mp4', '.wav'}:
        status = "❌ 阻擋 (非純影音格式)"
    else:
        is_legal = is_file_content_legal(path)
        status = "✅ 放行" if is_legal else "❌ 阻擋 (黑名單或缺乏雙重特徵)"
    print(f"[{status}] {f}")

print("\n=== 3. file_watcher.py 防護測試 (管線入口) ===")
raw_path = Path(test_dir)
for item in raw_path.iterdir():
    fname = item.name.lower()
    if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS:
        if any(bad in fname for bad in ["chunk_", "temp_", "extracted_", "_chunks", "逐字稿"]):
            print(f"[❌ 阻擋 (黑名單)] {item.name}")
        else:
            print(f"[✅ 成功接單] {item.name}")
    else:
        print(f"[❌ 阻擋 (副檔名不符)] {item.name}")

print("\n=== 清理環境 ===")
for f in mock_files:
    os.remove(os.path.join(test_dir, f))
os.rmdir(test_dir)
print("測試完成！")
