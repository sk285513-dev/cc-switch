import os
import re
import datetime

processed_dir = r"A:\processed_md"
if not os.path.exists(processed_dir):
    print("Directory A:\processed_md not found.")
    exit()

def parse_time(t_str):
    h, m, s, ms = map(int, re.split('[:,]', t_str))
    return h * 3600 + m * 60 + s + ms / 1000.0

def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

count = 0
for f in os.listdir(processed_dir):
    if not f.endswith('.srt'):
        continue
    filepath = os.path.join(processed_dir, f)
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            content = file.read()
            
        blocks = content.strip().split('\n\n')
        new_blocks = []
        global_offset = 0.0
        last_end = 0.0
        
        is_buggy = False
        
        for idx, block in enumerate(blocks):
            lines = block.split('\n')
            if len(lines) >= 3:
                times = re.findall(r'(\d{2}:\d{2}:\d{2},\d{3})', lines[1])
                if len(times) == 2:
                    start_t = parse_time(times[0])
                    end_t = parse_time(times[1])
                    
                    # Detect backward jump
                    if start_t + global_offset < last_end - 2.0:
                        is_buggy = True
                        # Jump backward detected! Calculate new offset to align it just after last_end
                        global_offset = last_end - start_t + 0.5
                    
                    new_start = start_t + global_offset
                    new_end = end_t + global_offset
                    
                    lines[1] = f"{format_time(new_start)} --> {format_time(new_end)}"
                    new_blocks.append('\n'.join(lines))
                    
                    last_end = new_end
        
        if is_buggy:
            # Re-number the blocks properly
            final_content = ""
            for i, blk in enumerate(new_blocks):
                lines = blk.split('\n')
                lines[0] = str(i + 1)
                final_content += '\n'.join(lines) + '\n\n'
                
            with open(filepath, 'w', encoding='utf-8') as out:
                out.write(final_content.strip() + '\n')
            count += 1
            print(f"Fixed in-place: {f}")
            
    except Exception as e:
        print(f"Error processing {f}: {e}")

print(f"Total buggy files fixed in-place: {count}")
