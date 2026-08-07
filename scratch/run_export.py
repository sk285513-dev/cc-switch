import sys
import os

export_script = "C:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/scripts_v6/export_plan_png.py"

with open(export_script, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace input_file and output_file
content = content.replace(
    r"input_file = r'C:\Users\temp\.gemini\antigravity\brain\8a6d8f31-3707-47f6-a39f-c53d88749feb\implementation_plan.md'",
    r"input_file = r'C:\Users\temp\antigravity\LexMind-Omni-法律實務-AI-工作站\PIPELINE_DEPENDENCIES.md'"
)

content = content.replace(
    r"html_file = r'C:\Users\temp\Downloads\LexMind-Omni_Implementation_Plan_Static.html'",
    r"html_file = r'C:\Users\temp\Downloads\LexMind-Omni_系統依賴地圖.html'"
)

content = content.replace(
    r"png_file = r'C:\Users\temp\Downloads\LexMind-Omni_Architecture.png'",
    r"png_file = r'C:\Users\temp\Downloads\LexMind-Omni_Architecture_Dependencies.png'"
)

# Wait, PIPELINE_DEPENDENCIES.md has TWO mermaid blocks!
# xport_plan_png.py currently only extracts the first one using e.search and replaces it using e.sub(r'`mermaid\n.*?\n`', img_tag, text, flags=re.DOTALL).
# Since there are TWO graphs in PIPELINE_DEPENDENCIES.md, e.sub with dotall and non-greedy .*? will replace BOTH blocks with the SAME image if we just use a single img_tag!
# Wait! Let's rewrite xport_plan_png.py to handle MULTIPLE mermaid blocks properly!
