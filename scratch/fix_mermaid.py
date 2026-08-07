import os
import re

input_file = "C:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/PIPELINE_DEPENDENCIES.md"

with open(input_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix mermaid syntax: add quotes around node labels that have special characters, or replace colons.
# E.g., G1[Group 1: 物流與規則<br>auto_ingest_bot] -> G1["Group 1 - 物流與規則<br>auto_ingest_bot"]
def fix_labels(match):
    node = match.group(1)
    label = match.group(2)
    # replace colon with hyphen, and wrap in quotes
    safe_label = label.replace(':', ' -')
    return f'{node}["{safe_label}"]'

# Replace [...] labels
content = re.sub(r'([A-Z0-9]+)\[([^\"\]]+)\]', fix_labels, content)
# Replace (...) labels if they have colons (though none currently do)
# content = re.sub(r'([A-Z0-9]+)\(([^\)\"]+)\)', lambda m: f'{m.group(1)}("{m.group(2).replace(":", " -")}")', content)

with open(input_file, 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed PIPELINE_DEPENDENCIES.md")
