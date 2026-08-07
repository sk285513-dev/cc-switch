import os
import sys
from pathlib import Path
import yaml

sys.path.append('C:\\LocalAI_Workstation\\scripts')
from workflow_helper import load_config

config = load_config()
stt_engine = config.get('settings', {}).get('stt_engine')
merge_engine = config.get('settings', {}).get('merge_engine')
high_model = config.get('api', {}).get('gemini_model_high_accuracy')

print(f"STT Engine: {stt_engine}")
print(f"Merge Engine: {merge_engine}")
print(f"High Accuracy Model: {high_model}")

if stt_engine == 'vertexai' or merge_engine == 'vertexai':
    print("DANGER: Vertex AI is still enabled!")
    sys.exit(1)
elif '2.5-pro' in high_model:
    print("DANGER: 2.5-pro model (with Thinking) is still enabled!")
    sys.exit(1)
else:
    print("SAFE: Vertex AI and 2.5-pro are fully disabled.")
    sys.exit(0)
