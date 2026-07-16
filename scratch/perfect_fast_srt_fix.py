import os
import glob
import json
import re
from pathlib import Path

def parse_timestamp_to_seconds(m_match):
    hr = int(m_match.group(1)) if m_match.group(1) else 0
    mn = int(m_match.group(2))
    sc = int(m_match.group(3))
    return hr * 3600 + mn * 60 + sc

def parse_transcript_into_timed_segments(text, chunk_start_time):
    pattern = r"\[(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\]"
    matches = list(re.finditer(pattern, text))
    
    segments = []
    if not matches:
        return [{"start": chunk_start_time, "end": chunk_start_time + 90.0, "text": text}]
        
    for i in range(len(matches)):
        m = matches[i]
        start_sec = parse_timestamp_to_seconds(m) + chunk_start_time
        
        start_idx = m.end()
        end_idx = matches[i+1].start() if i + 1 < len(matches) else len(text)
        seg_text = text[start_idx:end_idx].strip()
        
        seg_text = re.sub(r"^#+\s+", "", seg_text)
        seg_text = re.sub(r"\s+", " ", seg_text)
        
        if seg_text:
            segments.append({
                "start": start_sec,
                "text": seg_text
            })
            
    return segments

def format_srt_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def format_vtt_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

def main():
    manifests_dir = r"A:\manifests"
    manifests = glob.glob(os.path.join(manifests_dir, "task_*.json"))
    
    success_count = 0
    for mf in manifests:
        if "_chunks" in mf: continue
        
        try:
            with open(mf, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            task_id = data.get("task_id")
            if not task_id: continue
            
            srt_path = data.get("output_srt")
            vtt_path = data.get("output_vtt")
            
            if not srt_path: continue
            
            chunks_mf = os.path.join(manifests_dir, f"{task_id}_chunks.json")
            if not os.path.exists(chunks_mf): continue
            
            with open(chunks_mf, 'r', encoding='utf-8') as f:
                chunks_data = json.load(f)
                
            task_chunks_dir = os.path.join(r"A:\chunks", task_id)
            
            all_segments = []
            for i, chunk in enumerate(chunks_data):
                stem = Path(chunk["path"]).stem
                chunk_start = float(chunk.get("start_time", 0.0))
                
                if i + 1 < len(chunks_data):
                    chunk_end = float(chunks_data[i+1].get("start_time", 0.0))
                else:
                    chunk_end = float('inf')
                    
                chunk_txt_file = os.path.join(task_chunks_dir, f"{stem}.txt")
                
                if os.path.exists(chunk_txt_file):
                    with open(chunk_txt_file, "r", encoding="utf-8") as rf:
                        text = rf.read()
                    segs = parse_transcript_into_timed_segments(text, chunk_start)
                    
                    for seg in segs:
                        if chunk_start <= seg["start"] < chunk_end:
                            all_segments.append(seg)
            
            if not all_segments: continue
            
            # Global sort to completely fix any LLM out-of-order hallucinations
            all_segments.sort(key=lambda x: x["start"])
            
            # Calculate end times globally so everything connects seamlessly
            for i in range(len(all_segments) - 1):
                all_segments[i]["end"] = all_segments[i+1]["start"]
            if all_segments:
                all_segments[-1]["end"] = all_segments[-1]["start"] + 10.0
            
            # Write SRT
            with open(srt_path, "w", encoding="utf-8") as f:
                for idx, seg in enumerate(all_segments, 1):
                    start_str = format_srt_time(seg["start"])
                    end_str = format_srt_time(seg["end"])
                    f.write(f"{idx}\n{start_str} --> {end_str}\n{seg['text']}\n\n")
                    
            # Write VTT
            if vtt_path:
                with open(vtt_path, "w", encoding="utf-8") as f:
                    f.write("WEBVTT\n\n")
                    for idx, seg in enumerate(all_segments, 1):
                        start_str = format_vtt_time(seg["start"])
                        end_str = format_vtt_time(seg["end"])
                        f.write(f"{idx}\n{start_str} --> {end_str}\n{seg['text']}\n\n")
            
            success_count += 1
        except Exception as e:
            print(f"Failed on {mf}: {e}")
            
    print(f"Successfully generated CORRECT SRTs with chunk offsets for {success_count} files!")

if __name__ == "__main__":
    main()
