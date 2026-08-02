import os
import yaml
from google import genai
from google.genai import types
import time

with open('C:/LocalAI_Workstation/config.yaml', 'r', encoding='utf-8-sig') as f:
    config = yaml.safe_load(f)

v_project = config.get('settings', {}).get('vertexai_project')
v_loc = config.get('settings', {}).get('vertexai_location', 'us-central1')
v_cred_path = config.get('settings', {}).get('vertexai_credentials_path', '')
if v_cred_path:
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.join('C:/LocalAI_Workstation', v_cred_path)

client = genai.Client(vertexai=True, project=v_project, location=v_loc)
print('Client initialized:', client)

test_audio_path = r'A:\chunks\task_20260706_201825_03_9113\chunk_001__00-00_08-57.wav'

with open(test_audio_path, 'rb') as f:
    audio_bytes = f.read()

print('Read', len(audio_bytes), 'bytes of audio.')
audio_part = types.Part.from_bytes(data=audio_bytes, mime_type='audio/wav')

success_count = 0
for i in range(1, 4):
    print(f'\n--- Test Run {i} ---')
    try:
        start_time = time.time()
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[audio_part, '請將此音檔轉寫為繁體中文'],
        )
        elapsed = time.time() - start_time
        print(f'Test {i} Success! Took {elapsed:.2f} seconds.')
        
        # Save output to file to verify encoding
        with open('C:/LocalAI_Workstation/vertex_test_output.txt', 'a', encoding='utf-8-sig') as out_f:
            out_f.write(f'\n--- Test Run {i} ---\n')
            out_f.write(response.text[:200] + '...\n')
            
        success_count += 1
    except Exception as e:
        print(f'Test {i} Failed!')
        print('Exception:', str(e))
        time.sleep(2) # Backoff on failure

print(f'\n--- Summary ---')
print(f'Successful runs: {success_count} / 3')
