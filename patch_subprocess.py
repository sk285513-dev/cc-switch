import os
import re

directory = r'C:\LocalAI_Workstation\scripts_v6'
files_to_patch = [
    ('auto_healer.py', r'subprocess\.run\(\["taskkill", "/F", "/IM", "ffmpeg\.exe"\], capture_output=True\)', r'subprocess.run(["taskkill", "/F", "/IM", "ffmpeg.exe"], capture_output=True, creationflags=0x08000000)'),
    ('local_chunk_refiner.py', r'subprocess\.run\(\[sys\.executable, "scripts/merge_transcript\.py", "--task-id", task_id\], cwd="C:/LocalAI_Workstation", check=True\)', r'subprocess.run([sys.executable, "scripts/merge_transcript.py", "--task-id", task_id], cwd="C:/LocalAI_Workstation", check=True, creationflags=0x08000000)'),
    ('local_chunk_refiner.py', r'subprocess\.run\(\[sys\.executable, "scripts/markdown_formatter\.py", "--task-id", task_id\], cwd="C:/LocalAI_Workstation", check=True\)', r'subprocess.run([sys.executable, "scripts/markdown_formatter.py", "--task-id", task_id], cwd="C:/LocalAI_Workstation", check=True, creationflags=0x08000000)'),
    ('markdown_formatter.py', r'subprocess\.Popen\(\[sys\.executable, target_script\], cwd=os\.path\.dirname\(target_script\)\)', r'subprocess.Popen([sys.executable, target_script], cwd=os.path.dirname(target_script), creationflags=0x08000000)'),
    ('reindex_all.py', r'subprocess\.run\(\[sys\.executable, sync_script\], capture_output=False\)', r'subprocess.run([sys.executable, sync_script], capture_output=False, creationflags=0x08000000)'),
    ('reindex_all.py', r'subprocess\.run\(cmd, capture_output=True, text=True, encoding="utf-8-sig"\)', r'subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8-sig", creationflags=0x08000000)'),
    ('run_batch_local_refiner.py', r'subprocess\.run\(\[sys\.executable, "-u", "scripts/local_chunk_refiner\.py", "--task_id", task_id\], cwd="C:/LocalAI_Workstation", check=True\)', r'subprocess.run([sys.executable, "-u", "scripts/local_chunk_refiner.py", "--task_id", task_id], cwd="C:/LocalAI_Workstation", check=True, creationflags=0x08000000)'),
    ('test_stt.py', r'subprocess\.run\(\[\'python\', r\'C:\\LocalAI_Workstation\\scripts\\stt_runner\.py\', task_id\]\)', r'subprocess.run([\'python\', r\'C:\\LocalAI_Workstation\\scripts\\stt_runner.py\', task_id], creationflags=0x08000000)')
]

for filename, pattern, replacement in files_to_patch:
    filepath = os.path.join(directory, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8-sig') as f:
                f.write(new_content)
            print(f'Patched {filename}')
        else:
            print(f'No match in {filename}')
