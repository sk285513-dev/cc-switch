import re

with open('C:\\LocalAI_Workstation\\app.py', 'r', encoding='utf-8') as f:
    code = f.read()

replacements = {
    '#e0e7ff': '#1e3a8a',  # indigo-100 to blue-900
    '#a5b4fc': '#4338ca',  # indigo-300 to indigo-700
    '#d8b4fe': '#7e22ce',  # purple-300 to purple-700
    '#34d399': '#059669',  # emerald-400 to emerald-600
    '#60a5fa': '#2563eb',  # blue-400 to blue-600
    'color: white': 'color: #1f2937', # white text to dark gray
    'color: white;': 'color: #1f2937;',
}

for old, new in replacements.items():
    code = code.replace(old, new)

with open('C:\\LocalAI_Workstation\\app.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Colors updated for light theme!")
