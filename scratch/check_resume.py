import os
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

processed_dir = "A:/processed_md/"
manifests_dir = "A:/manifests/"
chunks_dir = "A:/chunks/"

expected_exts = ['.md', '.srt', '.vtt', '.txt', '_index.json']
MIN_FILE_SIZE_KB = 2.0

stems = set()
for f in os.listdir(processed_dir):
    if f.endswith('.md') and not f.startswith("00_"):
        stems.add(f[:-3])

failed_stems = set()
for stem in stems:
    missing = []
    too_small = []
    for ext in expected_exts:
        path = os.path.join(processed_dir, f"{stem}{ext}")
        if not os.path.exists(path):
            missing.append(ext)
        else:
            if os.path.getsize(path) / 1024.0 < MIN_FILE_SIZE_KB:
                too_small.append(ext)
    if missing or too_small:
        failed_stems.add(stem)

print(f"Total failed stems in processed_md: {len(failed_stems)}")

# Now find their manifests
found_manifests = []
for m_file in os.listdir(manifests_dir):
    if m_file.endswith("_chunks.json") or m_file == "queue.json": continue
    
    m_path = os.path.join(manifests_dir, m_file)
    try:
        with open(m_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Check if this manifest belongs to one of our failed stems
        src_name = data.get("source_name", "")
        stem = Path(src_name).stem
        # The processed output has some prefix like "[Course_chX]_stem" 
        # Wait, the processed_md stem format is usually exactly the same as the final output.
        # Actually, let's just check if the stem is IN the processed stem, or vice versa
        matched_stem = None
        for fs in failed_stems:
            if stem in fs or fs in stem:
                matched_stem = fs
                break
                
        if matched_stem:
            task_id = data.get("task_id")
            status = data.get("status")
            steps = data.get("steps", {})
            
            # Check chunks
            chunks_path = os.path.join(manifests_dir, f"{task_id}_chunks.json")
            completed_chunks = 0
            total_chunks = 0
            if os.path.exists(chunks_path):
                with open(chunks_path, "r", encoding="utf-8") as cf:
                    cdata = json.load(cf)
                    total_chunks = len(cdata)
                    completed_chunks = sum(1 for c in cdata if c.get("status") == "completed")
                    
            found_manifests.append({
                "stem": matched_stem,
                "task_id": task_id,
                "status": status,
                "completed_chunks": completed_chunks,
                "total_chunks": total_chunks,
                "steps": steps
            })
    except Exception as e:
        pass

print(f"Found {len(found_manifests)} matching manifests for the {len(failed_stems)} failed stems.")
if found_manifests:
    print("Sample of found manifests:")
    for m in found_manifests[:10]:
        print(f"  {m['stem']} -> Task: {m['task_id']}, Status: {m['status']}, STT Chunks: {m['completed_chunks']}/{m['total_chunks']}, Steps: {m['steps']}")
