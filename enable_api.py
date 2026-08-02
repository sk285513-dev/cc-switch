import os
import requests
import google.auth
from google.auth.transport.requests import Request

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'C:/LocalAI_Workstation/vertex_key.json'

try:
    credentials, project = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
    credentials.refresh(Request())
    
    headers = {
        'Authorization': f'Bearer {credentials.token}',
        'Content-Type': 'application/json'
    }
    
    print('Checking/Enabling aiplatform.googleapis.com for project:', project)
    
    # 1. Enable Vertex AI API
    url_enable = f'https://serviceusage.googleapis.com/v1/projects/{project}/services/aiplatform.googleapis.com:enable'
    resp_enable = requests.post(url_enable, headers=headers)
    print('Enable Vertex AI API response:', resp_enable.status_code, resp_enable.text)
    
    # 2. Enable Generative Language API (just in case)
    url_genlang = f'https://serviceusage.googleapis.com/v1/projects/{project}/services/generativelanguage.googleapis.com:enable'
    resp_genlang = requests.post(url_genlang, headers=headers)
    print('Enable Generative Language API response:', resp_genlang.status_code)
    
except Exception as e:
    print('Error:', e)
