import json, glob, sys; sys.path.append('C:/LocalAI_Workstation/scripts'); from duplicate_guard import is_already_ingested; 
for f in glob.glob('A:/manifests/quarantine/task_*.json'):
 if not f.endswith('_chunks.json'):
  if not is_already_ingested(json.load(open(f, encoding='utf-8')).get('source_path', '')):
   print(json.load(open(f, encoding='utf-8')).get('source_name', ''))
