import sys
import os
import yaml

sys.path.append('C:\\LocalAI_Workstation\\scripts')
from setup_wizard import update_config, CONFIG_PATH

def get_current_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def run_test():
    print('Starting Setup Wizard Configuration Test (v2.5 Generation)...')
    print(f'Using CONFIG_PATH: {CONFIG_PATH}')
    
    test_cases = [
        {
            'name': 'Option 1: Pure Free',
            'actions': [
                ('stt_engine', 'gemini'),
                ('merge_engine', 'gemini'),
                ('gemini_model_high_accuracy', 'gemini-2.5-flash')
            ]
        },
        {
            'name': 'Option 2: Mixed',
            'actions': [
                ('stt_engine', 'gemini'),
                ('merge_engine', 'vertexai'),
                ('gemini_model_high_accuracy', 'gemini-2.5-flash')
            ]
        },
        {
            'name': 'Option 3: Local Whisper',
            'actions': [
                ('stt_engine', 'local_whisper'),
                ('merge_engine', 'gemini'),
                ('gemini_model_high_accuracy', 'gemini-2.5-flash')
            ]
        },
        {
            'name': 'Option 4: Premium Vertex',
            'actions': [
                ('stt_engine', 'vertexai'),
                ('merge_engine', 'vertexai'),
                ('gemini_model_high_accuracy', 'gemini-2.5-pro')
            ]
        }
    ]
    
    try:
        for case in test_cases:
            print(f'\n--- Testing {case["name"]} ---')
            # Apply changes via setup_wizard's update_config function
            for key, value in case['actions']:
                update_config(key, value)
            
            # Read back using standard pyyaml
            current = get_current_config()
            
            # Verify
            stt = current.get('settings', {}).get('stt_engine')
            merge = current.get('settings', {}).get('merge_engine')
            model = current.get('api', {}).get('gemini_model_high_accuracy')
            
            print(f"Verified Config -> STT: {stt}, Merge: {merge}, Model: {model}")
            
            # Assert correct
            expected_stt = dict(case['actions'])['stt_engine']
            expected_merge = dict(case['actions'])['merge_engine']
            expected_model = dict(case['actions'])['gemini_model_high_accuracy']
            
            if stt != expected_stt or merge != expected_merge or model != expected_model:
                print('❌ FAILED: Values do not match expected!')
                return False
            print('✅ PASSED')
            
        print('\n🎉 All configuration paths successfully tested in sandbox. Models are CORRECT.')
        return True
        
    finally:
        print('\nRestoring User Selection (Option 2: Mixed)...')
        update_config('stt_engine', 'gemini')
        update_config('merge_engine', 'vertexai')
        update_config('gemini_model_high_accuracy', 'gemini-2.5-flash')
        print('Restoration complete.')

if __name__ == '__main__':
    success = run_test()
    sys.exit(0 if success else 1)
