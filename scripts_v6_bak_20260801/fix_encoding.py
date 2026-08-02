f = 'C:/LocalAI_Workstation/scripts/run_workflow.py'
with open(f, 'r', encoding='utf-8') as file:
    content = file.read()
content = content.replace('encoding=\"utf-8\"', 'encoding=\"utf-8-sig\"')
with open(f, 'w', encoding='utf-8') as file:
    file.write(content)
print('Done.')
