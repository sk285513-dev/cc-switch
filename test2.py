import codecs
import re
path = r'C:\LocalAI_Workstation\scripts_v6\kpi_monitor.py'
with codecs.open(path, 'r', 'utf-8') as f:
    content = f.read()

# I will find all instances of '(now - ' and replace them
print("Matches found:", re.findall(r'\(now - .*?\)', content))
