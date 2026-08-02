import re

with open('C:\\LocalAI_Workstation\\To_Format.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()

out_lines = []
in_code_block = False
lang = ''

for line_idx, orig_line in enumerate(lines):
    line = orig_line.rstrip('\n')
    
    # Check if this line has a code block start at the end of the line
    # like ... ``python
    match_start = re.search(r'(`{1,6})(python|diff|bash|sh|json|yaml|typescript|javascript|mermaid)\s*$', line, re.IGNORECASE)
    
    if not in_code_block:
        if match_start:
            # It's starting a code block
            in_code_block = True
            lang = match_start.group(2).lower()
            
            # If the line has text before the backticks, split it
            prefix = line[:match_start.start()].rstrip()
            if prefix:
                # But wait, what if the prefix starts with backticks? e.g. ``` - [x] ...
                # Let's clean up the prefix too
                prefix = re.sub(r'^`{1,6}\s*', '', prefix)
                # Remove 4-space indent if present
                if prefix.startswith('    '):
                    prefix = prefix[4:]
                out_lines.append(prefix)
            
            out_lines.append(f'```{lang}')
            continue
            
        # If not starting a code block, check for stray closing backticks that might actually be empty starts or just garbage
        if re.match(r'^\s*`{1,6}\s*$', line):
            # Stray backticks outside a code block? Ignore or treat as start of empty block?
            # Usually it's a messed up delimiter. Let's just drop it or treat as code block start if we really want, 
            # but maybe it's just leftover. Let's ignore it if it doesn't have a language.
            pass
        else:
            # Normal text
            # Clean up leading ``` if it leaked from a previous line
            line = re.sub(r'^`{1,6}\s*', '', line)
            
            # Remove 4-space indent
            if line.startswith('    '):
                line = line[4:]
            
            out_lines.append(line)
    else:
        # Inside code block
        # Check for end of code block
        # Usually it's a line with just backticks, or ` at the start
        if re.match(r'^\s*`{1,6}\s*$', line):
            in_code_block = False
            out_lines.append('```')
        elif match_start:
            # Another start inside a code block? This means the previous one wasn't closed.
            # Close the previous one, and start the new one
            out_lines.append('```')
            # Same logic as above for prefix
            prefix = line[:match_start.start()].rstrip()
            if prefix:
                out_lines.append(prefix)
            out_lines.append(f'```{match_start.group(2).lower()}')
        else:
            # Check if line contains end of block followed by normal text? Unlikely.
            out_lines.append(line)

# If still in code block at EOF, close it
if in_code_block:
    out_lines.append('```')

with open('C:\\LocalAI_Workstation\\Formatted.md', 'w', encoding='utf-8') as f:
    for line in out_lines:
        f.write(line + '\n')
