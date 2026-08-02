import os
import json

buffer_file = "C:\\LocalAI_Workstation\\chosen_paths_buffer.json"
paths = ["C:\\LocalAI_Workstation"]  # Test with this folder

os.makedirs(os.path.dirname(buffer_file), exist_ok=True)
with open(buffer_file, "w", encoding="utf-8-sig") as f:
    json.dump(paths, f, ensure_ascii=False, indent=4)
print("Buffer created.")
