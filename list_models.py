import os
import yaml
from google import genai

with open('C:/LocalAI_Workstation/config.yaml', 'r', encoding='utf-8-sig') as f:
    config = yaml.safe_load(f)

v_project = config.get('settings', {}).get('vertexai_project')
v_cred_path = config.get('settings', {}).get('vertexai_credentials_path', '')
if v_cred_path:
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.join('C:/LocalAI_Workstation', v_cred_path)

client = genai.Client(vertexai=True, project=v_project, location='us-central1')
try:
    models = client.models.list()
    for m in models:
        print(m.name)
except Exception as e:
    print('Exception:', str(e))
