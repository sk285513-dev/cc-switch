with open(r"C:\LocalAI_Workstation\scripts\robust_json.py", "r", encoding="utf-8-sig") as f:
    lines = f.readlines()
with open(r"C:\LocalAI_Workstation\scripts\robust_json.py", "w", encoding="utf-8-sig") as f:
    for line in lines:
        if not line.startswith("from robust_json import"):
            f.write(line)
