import os
import re
import shutil

drives = ["J:\\", "H:\\"]
processed_dir = r"A:\processed_md"

def parse_time(t_str):
    h, m, s, ms = map(int, re.split('[:,]', t_str))
    return h * 3600 + m * 60 + s + ms / 1000.0

def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

count_fixed = 0

for drive in drives:
    if not os.path.exists(drive):
        continue
    for root, dirs, files in os.walk(drive):
        for f in files:
            if f.endswith(".srt"):
                filepath = os.path.join(root, f)
                try:
                    with open(filepath, 'r', encoding='utf-8') as file:
                        content = file.read()
                    
                    blocks = content.strip().split('\n\n')
                    new_blocks = []
                    last_end_time = 0.0
                    modified = False
                    
                    for block in blocks:
                        lines = block.split('\n')
                        if len(lines) >= 3:
                            time_match = re.search(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})', lines[1])
                            if time_match:
                                start_t = parse_time(time_match.group(1))
                                end_t = parse_time(time_match.group(2))
                                
                                # 核心修復邏輯：如果發生時光倒流
                                if start_t < last_end_time:
                                    # 補償位移量 (讓這一段的開始時間硬是接在上一段之後)
                                    offset = last_end_time - start_t
                                    start_t += offset
                                    end_t += offset
                                    
                                    new_time_line = f"{format_time(start_t)} --> {format_time(end_t)}"
                                    lines[1] = new_time_line
                                    modified = True
                                
                                last_end_time = end_t
                        new_blocks.append('\n'.join(lines))
                        
                    if modified:
                        fixed_content = '\n\n'.join(new_blocks) + '\n'
                        # 原地覆寫原始備份碟的 SRT
                        with open(filepath, 'w', encoding='utf-8') as out_f:
                            out_f.write(fixed_content)
                        count_fixed += 1
                        print(f"Fixed time jumps in: {filepath}")
                        
                        # 同步覆寫到 A:\processed_md (確保管線與備份碟狀態一致)
                        if os.path.exists(processed_dir):
                            dest_path = os.path.join(processed_dir, f)
                            shutil.copy2(filepath, dest_path)
                            
                except Exception as e:
                    print(f"Error processing {filepath}: {e}")

print(f"Smart SRT Fix completed. Fixed {count_fixed} SRT files.")
