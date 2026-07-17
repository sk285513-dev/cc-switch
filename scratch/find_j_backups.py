import os
import json
from pathlib import Path

manifests_dir = r"A:\manifests"
for f in os.listdir(manifests_dir):
    if f.endswith(".json") and not f.endswith("_chunks.json") and f.startswith("task_"):
        p = os.path.join(manifests_dir, f)
        try:
            with open(p, 'r', encoding='utf-8') as jf:
                data = json.load(jf)
            if data.get("status") == "completed":
                source_path = data.get("source_path")
                output_md = data.get("output_markdown")
                if source_path and output_md:
                    backup_dir = os.path.dirname(source_path)
                    print(f"Task: {data.get('task_id')}")
                    print(f"Source file: {source_path}")
                    print(f"Backup directory: {backup_dir}")
                    if os.path.exists(backup_dir):
                        print("Files in backup directory:")
                        for bf in os.listdir(backup_dir):
                            # Print files in the directory that might be the backups
                            if bf.endswith(('.md', '.srt', '.vtt', '.txt', '.json')) or any(part in bf for part in ["index", "task"]):
                                print(f"  - {bf} ({os.path.getsize(os.path.join(backup_dir, bf)) / 1024:.2f} KB)")
                    else:
                        print("Backup directory does not exist or offline.")
                    break
        except Exception as e:
            pass
