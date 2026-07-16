import os
import glob
import re

def parse_timestamp_to_seconds(m_match):
    hr = int(m_match.group(1)) if m_match.group(1) else 0
    mn = int(m_match.group(2))
    sc = int(m_match.group(3))
    return hr * 3600 + mn * 60 + sc

def parse_transcript_into_timed_segments(text):
    pattern = r"\[(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\]"
    matches = list(re.finditer(pattern, text))
    
    segments = []
    if not matches:
        return []
        
    for i in range(len(matches)):
        m = matches[i]
        start_sec = parse_timestamp_to_seconds(m)
        
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
            
    for i in range(len(segments) - 1):
        segments[i]["end"] = segments[i+1]["start"]
    if segments:
        segments[-1]["end"] = segments[-1]["start"] + 10.0
        
    return segments

def format_srt_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def main():
    target_dir = r"A:\processed_md"
    md_files = glob.glob(os.path.join(target_dir, "*.md"))
    
    success_count = 0
    for md_path in md_files:
        try:
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 找到逐字稿區域
            marker = "## 🎙️ 去冗餘精校逐字稿 (Cleaned Transcript)"
            if marker not in content:
                continue
                
            transcript_text = content.split(marker)[-1].strip()
            segments = parse_transcript_into_timed_segments(transcript_text)
            
            if not segments:
                continue
                
            # 檢查是否原本的 SRT 有問題 (如果沒有問題可以跳過，但全做也沒差，才幾毫秒)
            base_path = os.path.splitext(md_path)[0]
            srt_path = base_path + ".srt"
            
            # 生成 SRT
            with open(srt_path, 'w', encoding='utf-8') as f:
                for idx, seg in enumerate(segments, 1):
                    start_str = format_srt_time(seg['start'])
                    end_str = format_srt_time(seg['end'])
                    f.write(f"{idx}\n{start_str} --> {end_str}\n{seg['text']}\n\n")
            
            success_count += 1
            if success_count % 20 == 0:
                print(f"Processed {success_count} files...")
                
        except Exception as e:
            print(f"Error processing {md_path}: {e}")
            
    print(f"Done! Successfully instantly rebuilt {success_count} SRT files from Markdown sources.")

if __name__ == "__main__":
    main()
