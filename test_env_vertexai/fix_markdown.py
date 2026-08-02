import re
import os

file_path = r'C:\Users\temp\antigravity\LexMind-Omni-法律實務-AI-工作站\Obsidian_Vault\基於涵蓋陣列與_DOM_狀態感知之高併發法律系統自動化視覺測試框架設計與實作.md'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

out_lines = []
in_code_block = False

for i, line in enumerate(lines):
    # Match code block start
    match = re.match(r'^\s*`{1,3}(mermaid|python|vbscript|markdown|bash|json)\s*$', line)
    if match:
        lang = match.group(1)
        # Rule 25: must have 4 spaces indentation, and an empty line before it if it's the start
        if len(out_lines) > 0 and out_lines[-1].strip() != '':
            out_lines.append('\n')
        out_lines.append(f'    ```{lang}\n')
        in_code_block = True
        continue
    
    # Detect end of code block (could be `, ``, ``` on its own line)
    if in_code_block and re.match(r'^\s*`{1,3}\s*$', line):
        out_lines.append('    ```\n')
        # Rule 25: must have an empty line after it
        out_lines.append('\n')
        in_code_block = False
        continue

    # Clean up random solitary single/double backticks that are not meant to be code blocks
    if not in_code_block and re.match(r'^\s*`{1,3}\s*$', line):
        continue

    # Clean up multiple empty lines
    if line.strip() == '' and len(out_lines) > 0 and out_lines[-1].strip() == '':
        continue

    if in_code_block:
        # If line has content, make sure it is indented by at least 4 spaces
        if line.strip() != '':
            stripped = line.lstrip()
            # If the original line had less than 4 spaces, force it to 4 + its original indent (or just 4)
            # Actually, standardizing to 8 spaces (4 for block, 4 for content) is safer for mermaid inside lists.
            # But let's just prepend 4 spaces to everything to be safe.
            # Wait, if we prepend 4 spaces to everything in the block, it will shift everything right.
            # Let's see how many leading spaces it currently has.
            current_spaces = len(line) - len(line.lstrip(' '))
            if current_spaces < 4:
                line = ' ' * 4 + line.lstrip()
            elif current_spaces == 4 and lang == 'mermaid':
                # Mermaid flowcharts need to be indented inside the block
                line = ' ' * 8 + line.lstrip()

    out_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(out_lines)

print("Fixed formatting!")
