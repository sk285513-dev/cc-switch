with open('C:/LocalAI_Workstation/app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'st.session_state.agent_instance = get_legal_agent_singleton()' in line:
        lines.insert(i, '        st.write("Initializing Agent...")\n')
        lines.insert(i + 2, '        st.write("Agent initialized! Now loading init_docs...")\n')
        break

for i, line in enumerate(lines):
    if 'st.session_state.agent_instance.law_coll.upsert(' in line:
        lines.insert(i, '            st.write("Upserting init_docs...")\n')
        break

with open('C:/LocalAI_Workstation/app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
