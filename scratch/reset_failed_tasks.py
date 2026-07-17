import os
import json
from pathlib import Path

manifests_dir = Path("A:/manifests")
if manifests_dir.exists():
    json_files = list(manifests_dir.glob("task_*.json"))
    reset_count = 0
    for p in json_files:
        if p.name.endswith("_chunks.json"):
            continue
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if data.get("status") == "failed":
                data["status"] = "pending"
                if "error" in data:
                    del data["error"]
                if "steps" in data:
                    for k in data["steps"]:
                        data["steps"][k] = "initial"
                
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                reset_count += 1
                print(f"Reset task: {p.name}")
        except Exception as e:
            print(f"Error resetting {p.name}: {e}")
    print(f"Successfully reset {reset_count} failed tasks.")
else:
    print("A:/manifests directory does not exist.")
