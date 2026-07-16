import os
import re
import json

processed_dir = r"A:\processed_md"

banned_words = ["地政治", "消滅實效", "格論", "遞贈式"]
fillers = ["那個", "然後", "就是說"]

def check_repetition(text):
    # Find any substring of at least 15 chars that repeats more than 4 times
    match = re.search(r'(.{15,})(?:\s*\1){4,}', text)
    return match.group(1) if match else None

issues = []

for f in os.listdir(processed_dir):
    if not f.endswith('.txt'):
        continue
        
    stem = f[:-4]
    txt_path = os.path.join(processed_dir, f)
    json_path = os.path.join(processed_dir, f"{stem}_index.json")
    
    lesson_issues = []
    
    try:
        with open(txt_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
        # 1. 嚴重重複幻覺 (Hallucination loop)
        rep = check_repetition(content)
        if rep:
            lesson_issues.append(f"Severe repetition detected (Hallucination loop): '{rep[:30]}...'")
            
        # 2. 嚴格驗收標準：同音錯字
        for bw in banned_words:
            if bw in content:
                lesson_issues.append(f"Violated acceptance criteria: Found banned homophone '{bw}'")
                
        # 3. 嚴格驗收標準：口語贅字過多
        filler_count = sum(content.count(fw) for fw in fillers)
        if filler_count > 30: # If there are over 30 filler words, the filtering failed.
            lesson_issues.append(f"Failed filler word filtering: Found {filler_count} filler words")
            
        # 4. 長度異常 (Content ratio)
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as jf:
                idx = json.load(jf)
                duration = idx.get("duration_sec", 0)
                if duration > 0:
                    words_per_minute = len(content) / (duration / 60)
                    if words_per_minute < 50:
                        lesson_issues.append(f"Abnormally short transcript: only {words_per_minute:.1f} chars/min. (Possible missing chunks)")
                    elif words_per_minute > 500:
                        lesson_issues.append(f"Abnormally long transcript: {words_per_minute:.1f} chars/min. (Possible hallucination loop)")
                        
    except Exception as e:
        lesson_issues.append(f"Error reading file: {e}")
        
    if lesson_issues:
        issues.append({"file": f, "issues": lesson_issues})

# Write markdown report
report_path = r"C:\LocalAI_Workstation\scratch\deep_diagnostic_report.md"
with open(report_path, "w", encoding="utf-8") as out:
    out.write("# 課程深度品質診斷報告\n\n")
    if not issues:
        out.write("未發現任何嚴重品質瑕疵。\n")
    else:
        out.write(f"共發現 {len(issues)} 堂課存在「品質瑕疵」，建議重做：\n\n")
        for issue in issues:
            out.write(f"### {issue['file']}\n")
            for reason in issue['issues']:
                out.write(f"- {reason}\n")
            out.write("\n")
            
print(f"Deep scan complete. Found {len(issues)} flawed files.")
