import sys
import codecs

with codecs.open('C:\\LocalAI_Workstation\\components\\settings_view.py', 'r', 'utf-8') as f:
    lines = f.readlines()

new_lines = []
in_form = False
for line in lines:
    if 'with st.form(\"settings_form\"):' in line:
        new_lines.append(line.replace('with st.form(\"settings_form\"):', '# removed st.form'))
        in_form = True
        continue
        
    if in_form:
        if line.startswith('    ') or line.strip() == '':
            dedented_line = line[4:] if len(line) >= 4 and line.startswith('    ') else line
            if 'st.form_submit_button' in dedented_line:
                dedented_line = dedented_line.replace('st.form_submit_button', 'st.button')
            new_lines.append(dedented_line)
        else:
            in_form = False
            new_lines.append(line)
    else:
        new_lines.append(line)

with codecs.open('C:\\LocalAI_Workstation\\components\\settings_view.py', 'w', 'utf-8') as f:
    f.writelines(new_lines)
print('Fixed!')
