from google import genai
from google.genai import types
import yaml
import os

with open('C:/LocalAI_Workstation/config.yaml', 'r', encoding='utf-8-sig') as f:
    config = yaml.safe_load(f)

v_project = config.get('settings', {}).get('vertexai_project')
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'C:/LocalAI_Workstation/vertex_key.json'

models_to_test = ['gemini-1.5-flash', 'gemini-1.5-flash-002', 'gemini-1.5-pro']
locations_to_test = ['us-central1', 'us-east4', 'asia-east1', 'asia-northeast1']

for loc in locations_to_test:
    client = genai.Client(vertexai=True, project=v_project, location=loc)
    print(f'\n--- Testing Location: {loc} ---')
    for model_name in models_to_test:
        try:
            print(f'Testing {model_name}...', end=' ')
            response = client.models.generate_content(
                model=model_name,
                contents='Hello',
            )
            print('SUCCESS!')
            break # If one model works in this location, move to next location
        except Exception as e:
            print(f'FAILED: {e}')
