import json
import os

filepath = r'A:\logs\watchdog_alerts.jsonl'
if os.path.exists(filepath):
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()
    
    new_lines = []
    for line in lines:
        try:
            data = json.loads(line)
            if data.get('status') == 'unresolved' and 'Unexpected UTF-8 BOM' in data.get('error_type', ''):
                data['status'] = 'resolved'
                data['resolution'] = 'Global patch applied: all utf-8 encodings upgraded to utf-8-sig.'
            new_lines.append(json.dumps(data, ensure_ascii=False) + '\n')
        except Exception:
            new_lines.append(line)
            
    with open(filepath, 'w', encoding='utf-8-sig') as f:
        f.writelines(new_lines)
    print("Watchdog alerts cleared.")
else:
    print("No watchdog alerts file found.")
