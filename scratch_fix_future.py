import os

files_to_fix = [
    r"C:\LocalAI_Workstation\scripts\evaluate.py",
    r"C:\LocalAI_Workstation\scripts\model_router.py"
]

for file in files_to_fix:
    with open(file, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()
        
    new_lines = []
    import_stmt = ""
    for line in lines:
        if line.startswith("from robust_json import"):
            import_stmt = line
        else:
            new_lines.append(line)
            
    # Now find where to insert
    insert_idx = 0
    for i, line in enumerate(new_lines):
        if line.startswith("from __future__"):
            insert_idx = i + 1
            break
            
    if insert_idx > 0 and import_stmt:
        new_lines.insert(insert_idx, import_stmt)
        with open(file, "w", encoding="utf-8-sig") as f:
            f.writelines(new_lines)
        print(f"Fixed {file}")
