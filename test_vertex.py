from google import genai
from google.genai import types
import yaml

with open('C:/LocalAI_Workstation/config.yaml', 'r', encoding='utf-8-sig') as f:
    config = yaml.safe_load(f)

v_project = config.get('settings', {}).get('vertexai_project')
v_loc = config.get('settings', {}).get('vertexai_location', 'us-central1')
v_cred_path = config.get('settings', {}).get('vertexai_credentials_path', '')
if v_cred_path:
    import os
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.join('C:/LocalAI_Workstation', v_cred_path)

client = genai.Client(vertexai=True, project=v_project, location=v_loc)
print('Client initialized:', client)

try:
    with open(r'A:\chunks\task_20260706_201825_03_9113\chunk_001__00-00_08-57.wav', 'rb') as f:
        audio_bytes = f.read()
    print('Read', len(audio_bytes), 'bytes')
    audio_part = types.Part.from_bytes(data=audio_bytes, mime_type='audio/wav')
    print('Calling generate_content...')
    response = client.models.generate_content(
        model='gemini-1.5-pro',  # Try a known Vertex model
        contents=[audio_part, '請將此音檔轉寫為繁體中文'],
    )
    print('Success:', response.text[:100])
except Exception as e:
    import traceback
    print('Exception:', str(e))
    traceback.print_exc()
