import re

with open('C:\\LocalAI_Workstation\\app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Replace hardcoded dark background colors
code = re.sub(r'background-color:\s*#[0-9a-fA-F]+;?', '', code)
# Replace hardcoded dark border colors
code = re.sub(r'border:\s*1px\s*solid\s*#[0-9a-fA-F]+;?', 'border: 1px solid #e5e7eb;', code)
# Replace specific dark hexes:
code = code.replace('#111827', 'transparent')
code = code.replace('#1f2937', '#e5e7eb')
code = code.replace('#1e1b4b', '#f3f4f6')
code = code.replace('#030712', '#f9fafb')
code = code.replace('#374151', '#d1d5db')
code = code.replace('color: #ffffff;', 'color: inherit;')
code = code.replace('color: #e5e7eb;', 'color: inherit;')
code = code.replace('color: #9ca3af;', 'color: #6b7280;')

# Add the JS injection for fixing the translation popup
inject_code = """
import streamlit.components.v1 as components
components.html(
    '''
    <script>
    window.parent.document.documentElement.lang = 'zh-TW';
    </script>
    ''',
    width=0,
    height=0,
)
"""

if 'st.markdown(\'<meta name="google" content="notranslate">\', unsafe_allow_html=True)' in code:
    code = code.replace(
        'st.markdown(\'<meta name="google" content="notranslate">\', unsafe_allow_html=True)',
        'st.markdown(\'<meta name="google" content="notranslate">\', unsafe_allow_html=True)\n' + inject_code
    )

with open('C:\\LocalAI_Workstation\\app.py', 'w', encoding='utf-8') as f:
    f.write(code)
print('Patched app.py successfully')
