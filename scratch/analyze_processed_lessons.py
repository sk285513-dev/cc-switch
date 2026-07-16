import os
import re

processed_dir = r"A:\processed_md"

def parse_time(t_str):
    h, m, s, ms = map(int, re.split('[:,]', t_str))
    return h * 3600 + m * 60 + s + ms / 1000.0

issues = []

if not os.path.exists(processed_dir):
    print("Directory not found.")
else:
    for f in os.listdir(processed_dir):
        if not f.endswith('.srt'):
            continue
            
        stem = f[:-4]
        filepath = os.path.join(processed_dir, f)
        
        # Check if companion files exist
        has_md = os.path.exists(os.path.join(processed_dir, f"{stem}.md"))
        has_txt = os.path.exists(os.path.join(processed_dir, f"{stem}.txt"))
        
        lesson_issues = []
        if not has_md:
            lesson_issues.append("Missing .md file")
        if not has_txt:
            lesson_issues.append("Missing .txt file")
            
        # Analyze SRT content
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                content = file.read()
                
            blocks = content.strip().split('\n\n')
            last_end = 0.0
            overlap_count = 0
            jump_count = 0
            long_sub_count = 0
            
            for block in blocks:
                lines = block.split('\n')
                if len(lines) >= 3:
                    time_match = re.search(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})', lines[1])
                    if time_match:
                        start_t = parse_time(time_match.group(1))
                        end_t = parse_time(time_match.group(2))
                        
                        if start_t < last_end:
                            jump_count += 1
                        if end_t - start_t > 30.0:  # A single subtitle lasting over 30 seconds is highly suspicious
                            long_sub_count += 1
                            
                        # Subtitle text length
                        text_len = sum(len(line) for line in lines[2:])
                        if text_len > 200: # Over 200 characters in one subtitle block
                            long_sub_count += 1
                            
                        last_end = end_t
                        
            if jump_count > 0:
                lesson_issues.append(f"{jump_count} unresolved time jumps")
            if long_sub_count > 0:
                lesson_issues.append(f"{long_sub_count} suspiciously long subtitles (hallucination or missing chunks)")
                
        except Exception as e:
            lesson_issues.append(f"Parse error: {str(e)}")
            
        if lesson_issues:
            issues.append({"file": f, "issues": lesson_issues})

# Write markdown report
with open(r"C:\LocalAI_Workstation\scratch\diagnostic_report.md", "w", encoding="utf-8") as out:
    out.write("# 課程健康度診斷報告\n\n")
    if not issues:
        out.write("目前檢查的課程皆未發現明顯格式錯誤。\n")
    else:
        out.write(f"共發現 {len(issues)} 堂課存在潛在問題：\n\n")
        for issue in issues:
            out.write(f"### {issue['file']}\n")
            for reason in issue['issues']:
                out.write(f"- {reason}\n")
            out.write("\n")
            
print(f"Scanned complete. Found {len(issues)} files with potential issues.")
