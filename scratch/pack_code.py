import os

files_to_pack = [
    r"scripts\utils\key_manager.py",
    r"scripts\quota_manager.py",
    r"scripts\vault.py",
    r"scripts\tasks\worker.py",
    r"scripts\orchestrator\batch_runner.py",
    r"scripts\auto_verify.py"
]

base_dir = r"C:\Users\temp\antigravity\LexMind-Omni-法律實務-AI-工作站"
output_file = os.path.join(base_dir, "scratch", "workflow_code_bundle_for_review.md")

with open(output_file, "w", encoding="utf-8") as out_f:
    out_f.write("# 核心工作流程原始碼打包 (Workflow Code Bundle for Expert Review)\n\n")
    out_f.write("此文件包含了 LexMind-Omni 系統中，與最新計畫書相關的端到端核心工作流程原始碼。請專家依據此最新狀態進行深度審查。\n\n")
    
    for rel_path in files_to_pack:
        abs_path = os.path.join(base_dir, rel_path)
        out_f.write(f"## 檔案：`{rel_path}`\n")
        out_f.write("```python\n")
        if os.path.exists(abs_path):
            with open(abs_path, "r", encoding="utf-8") as in_f:
                out_f.write(in_f.read())
        else:
            out_f.write(f"# [錯誤] 找不到檔案：{abs_path}\n")
        out_f.write("\n```\n\n")

print(f"Packed {len(files_to_pack)} files into {output_file}")
