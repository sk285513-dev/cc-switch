import os
import glob
import re
import json
import sys
import codecs
from datetime import datetime

# Fix CP950 printing issues on Windows
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

def parse_time(time_str):
    try:
        time_obj = datetime.strptime(time_str.strip(), '%H:%M:%S,%f')
        return time_obj.hour * 3600 + time_obj.minute * 60 + time_obj.second + time_obj.microsecond / 1000000.0
    except ValueError:
        return 0

def analyze_srt(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return 0, False
        
    pattern = r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})'
    matches = re.findall(pattern, content)
    
    max_duration = 0
    for start_str, end_str in matches:
        start_sec = parse_time(start_str)
        end_sec = parse_time(end_str)
        duration = end_sec - start_sec
        if duration > max_duration:
            max_duration = duration
            
    has_unparsed_tags = bool(re.search(r'\[\d{1,2}:\d{2}\]', content))
    return max_duration, has_unparsed_tags

def load_manifests():
    manifests_dir = r"A:\manifests"
    mapping = {}
    for mf in glob.glob(os.path.join(manifests_dir, "task_*.json")):
        # chunk manifests typically have _chunks in the name, we want the main one
        if "_chunks" in mf: continue
        try:
            with open(mf, 'r', encoding='utf-8') as f:
                data = json.load(f)
            srt_path = data.get("output_srt", "")
            if srt_path:
                task_id = data.get("task_id", "")
                mapping[os.path.normpath(srt_path)] = task_id
        except Exception:
            pass
    return mapping

def main():
    target_dir = r"A:\processed_md"
    srt_files = glob.glob(os.path.join(target_dir, "*.srt"))
    manifest_mapping = load_manifests()
    
    buggy_tasks = []
    
    print(f"Scanning {len(srt_files)} SRT files...")
    for srt in srt_files:
        max_duration, has_tags = analyze_srt(srt)
        if max_duration > 90 or has_tags:
            norm_srt = os.path.normpath(srt)
            task_id = manifest_mapping.get(norm_srt, "UNKNOWN_TASK_ID")
            buggy_tasks.append({
                "srt": os.path.basename(srt),
                "duration": max_duration,
                "has_tags": has_tags,
                "task_id": task_id
            })
            
    print("\n=== Affected Courses (SRT) ===")
    for b in buggy_tasks:
        print(f"File: {b['srt']}")
        print(f"  - Task ID: {b['task_id']}")
        print(f"  - Max Block Duration: {b['duration']:.1f} s")
        print("-" * 40)
        
    print(f"Total: {len(buggy_tasks)} / {len(srt_files)} courses affected by the Regex Bug!")
    
    if buggy_tasks:
        print("\n\n[Recovery Command]")
        print("Run the following commands to instantly fix the SRTs without API costs:\n")
        print("--- COPY BELOW TO POWERSHELL ---")
        for b in buggy_tasks:
            if b['task_id'] != "UNKNOWN_TASK_ID":
                print(f"python C:\\LocalAI_Workstation\\scripts\\markdown_formatter.py --task-id {b['task_id']}")
        print("--------------------------------")
        
        # Also write the batch script to a .ps1 file for convenience
        batch_file = r"C:\LocalAI_Workstation\scratch\fix_all_srt.ps1"
        with open(batch_file, "w", encoding="utf-8") as bf:
            for b in buggy_tasks:
                if b['task_id'] != "UNKNOWN_TASK_ID":
                    bf.write(f"python C:\\LocalAI_Workstation\\scripts\\markdown_formatter.py --task-id {b['task_id']}\n")
        print(f"Batch script also saved to {batch_file}")

if __name__ == "__main__":
    main()
