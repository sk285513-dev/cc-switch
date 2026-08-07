import os
from google import genai
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.abspath('config/vertex_key.json')
try:
    client = genai.Client(vertexai=True, project='[REDACTED_PROJECT_ID]', location='us-central1')
    response = client.models.generate_content(model='gemini-2.5-flash', contents='hello')
    print('SUCCESS:', response.text)
except Exception as e:
    print('ERROR:', repr(e))
