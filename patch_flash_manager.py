import re

with open('C:\\LocalAI_Workstation\\app.py', 'r', encoding='utf-8-sig') as f:
    content = f.read()

insert_marker = "st.markdown('<meta name=\"google\" content=\"notranslate\">', unsafe_allow_html=True)"
flash_manager_code = """
# --- 全域 Flash Message Manager ---
def flash_message(msg_type, msg):
    if "flash_messages" not in st.session_state:
        st.session_state.flash_messages = []
    st.session_state.flash_messages.append((msg_type, msg))

def flash_and_rerun(msg_type, msg):
    flash_message(msg_type, msg)
    st.rerun()

if "flash_messages" in st.session_state and st.session_state.flash_messages:
    for m_type, m_text in st.session_state.flash_messages:
        if m_type == "success": st.success(m_text)
        elif m_type == "error": st.error(m_text)
        elif m_type == "warning": st.warning(m_text)
        elif m_type == "info": st.info(m_text)
    st.session_state.flash_messages = []
# ---------------------------------
"""
if "# --- 全域 Flash Message Manager ---" not in content:
    content = content.replace(insert_marker, insert_marker + "\n" + flash_manager_code)

def replacer(match):
    indent = match.group(1)
    msg_type = match.group(2)
    msg_content = match.group(3)
    return f'{indent}flash_and_rerun("{msg_type}", {msg_content})'

# Catch st.success/warning/error/info (...) followed by optional time.sleep and st.rerun
pattern = r'([ \t]*)st\.(success|warning|error|info)\((.*?)\)\n(?:[ \t]*time\.sleep\([^)]*\)\n)*[ \t]*st\.rerun\(\)'
content, count = re.subn(pattern, replacer, content)
print(f"Replaced {count} occurrences of ghost clicks.")

# Clean up my previous manual fix for the manual button
manual_fix_pattern1 = r'([ \t]*)if st\.session_state\.get\("ingest_success_msg"\):\n[ \t]*st\.success\(st\.session_state\.ingest_success_msg\)\n[ \t]*st\.session_state\.ingest_success_msg = ""\n'
content = re.sub(manual_fix_pattern1, '', content)

manual_fix_pattern2 = r'([ \t]*)st\.session_state\.ingest_success_msg = (.*?)\n([ \t]*)st\.session_state\.chosen_batch_paths = \[\]\n([ \t]*)save_paths_to_buffer\(\[\]\)\n'
def replacer2(match):
    indent = match.group(1)
    msg = match.group(2)
    return f'{indent}st.session_state.chosen_batch_paths = []\n{indent}save_paths_to_buffer([])\n{indent}flash_and_rerun("success", {msg})\n'
content = re.sub(manual_fix_pattern2, replacer2, content)

with open('C:\\LocalAI_Workstation\\app.py', 'w', encoding='utf-8-sig') as f:
    f.write(content)

print("Patching completed.")
