import os
import re

filepath = r"A:\processed_md\[民事訴訟法ˋ_ch10]_預約 10 2024-09-30 14-02-24-012.srt"

with open(filepath, 'r', encoding='utf-8') as file:
    content = file.read()
    
    # Extract all timestamps like 00:11:11,000
    times = re.findall(r'(\d{2}):(\d{2}):(\d{2}),\d{3} --> (\d{2}):(\d{2}):(\d{2}),\d{3}', content)
    
    last_seconds = 0
    for i, start_t in enumerate(times):
        h, m, s = int(start_t[0]), int(start_t[1]), int(start_t[2])
        current_seconds = h * 3600 + m * 60 + s
        
        if current_seconds < last_seconds - 5: # sudden drop backwards
            print(f"Bug found at transition: {times[i-1]} -> {times[i]}")
            break
        last_seconds = current_seconds
