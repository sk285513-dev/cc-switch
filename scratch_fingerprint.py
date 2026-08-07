import hashlib
import os

files = [
    r"LexMind_一鍵正式啟動.ps1",
    r"LexMind_一鍵完全關閉系統.ps1",
    r".streamlit\config.toml",
    r"scripts_v6\run_workflow.py",
    r"app_v6.py",
    r"Launch_Isolated.vbs",
    r"kpi_runner.ps1",
    r"scripts_v6\progress_dashboard.py"
]

csv_content = '"File","Path","SHA256"\n'
for f in files:
    full_path = os.path.join("C:/LocalAI_Workstation", f)
    if os.path.exists(full_path):
        with open(full_path, "rb") as file:
            h = hashlib.sha256(file.read()).hexdigest().upper()
        name = os.path.basename(f)
        csv_content += f'"{name}","C:\\LocalAI_Workstation\\{f}","{h}"\n'

with open("C:/LocalAI_Workstation/v6.1_script_fingerprints.csv", "w", encoding="utf-8") as f:
    f.write(csv_content)
print("Generated v6.1_script_fingerprints.csv for 8 core scripts.")
