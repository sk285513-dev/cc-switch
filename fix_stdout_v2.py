import glob
import re

pattern = re.compile(r\"\"\"(?:if hasattr\(sys,\s*['\"]stdout['\"]\)\s*and\s*)?if hasattr\(sys\.stdout,\s*['\"]reconfigure['\"]\):\s*sys\.stdout\.reconfigure\(encoding=['\"]utf-8['\"],\s*errors=['\"]replace['\"]\)\s*(?:if hasattr\(sys,\s*['\"]stderr['\"]\)\s*and\s*)?if hasattr\(sys\.stderr,\s*['\"]reconfigure['\"]\):\s*sys\.stderr\.reconfigure\(encoding=['\"]utf-8['\"],\s*errors=['\"]replace['\"]\)\"\"\", re.MULTILINE)

new_str = '''try:
    if hasattr(sys, 'stdout') and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys, 'stderr') and hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass'''

for f in glob.glob('scripts/*.py') + ['app.py', 'bot_ultimate_real_crawler.py', 'C:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/scripts/*.py']:
    try:
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
            content_norm = content.replace('\r\n', '\n')
            
        if 'sys.stdout.reconfigure' in content_norm and 'try:' not in content_norm[:500]:
            match = pattern.search(content_norm)
            if match:
                new_content = content_norm[:match.start()] + new_str + content_norm[match.end():]
                with open(f, 'w', encoding='utf-8') as file:
                    file.write(new_content)
                print(f'Fixed {f}')
            else:
                print(f'Manual fix needed for {f}')
    except Exception as e:
        pass
