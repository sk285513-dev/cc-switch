import os
import glob

for file in glob.glob(r"C:\LocalAI_Workstation\scripts\**\*.py", recursive=True):
    with open(file, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()
        
    for i in range(len(lines)-1):
        if lines[i].strip() == "try:" and lines[i+1].strip().startswith("except "):
            print(f"Empty try block in {file}:{i+1}")
