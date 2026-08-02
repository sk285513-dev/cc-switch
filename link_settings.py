with open('C:/LocalAI_Workstation/app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'import streamlit as st' in line:
        lines.insert(i + 1, 'from components.settings_view import render_settings_page\n')
        break

for i, line in enumerate(lines):
    if 'with tab_admin:' in line:
        lines.insert(i + 1, '    render_settings_page()\n')
        lines.insert(i + 2, '    st.divider()\n')
        break

with open('C:/LocalAI_Workstation/app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
