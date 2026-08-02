import os

path = r'C:\Python312\Lib\site-packages\streamlit\static\index.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('<html lang="en">', '<html lang="zh-TW" translate="no">')
if '<meta name="google" content="notranslate">' not in content:
    content = content.replace('<head>', '<head>\n    <meta name="google" content="notranslate">')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Patched Streamlit index.html!')
