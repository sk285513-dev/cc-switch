import json, glob, sys; sys.path.append('C:/LocalAI_Workstation/scripts'); from duplicate_guard import is_already_ingested; v=0; p=0; 
for f in glob.glob('A:/manifests/quarantine/task_*.json'):
 if not f.endswith('_chunks.json'):
  if is_already_ingested(json.load(open(f, encoding='utf-8')).get('source_path', '')):
   p+=1
  else:
   v+=1
print(f'Virgin: {v}, Processed: {p}')
