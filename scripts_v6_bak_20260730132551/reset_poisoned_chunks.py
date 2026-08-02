import json
import json
import glob
import os

manifest_dir = r'A:\manifests'
chunk_files = glob.glob(os.path.join(manifest_dir, '*_chunks.json'))

reset_chunks = 0
reset_tasks = 0

for f in chunk_files:
    try:
        with open(f, 'r', encoding='utf-8-sig') as file:
            chunks = json.load(file)
            
        task_poisoned = False
        for chunk in chunks:
            if chunk.get('status') in ['completed', 'stt_done'] and not chunk.get('text'):
                chunk['status'] = 'pending'
                chunk['text'] = ''
                reset_chunks += 1
                task_poisoned = True
                
        if task_poisoned:
            with open(f, 'w', encoding='utf-8-sig') as file:
                json.dump(chunks, file, ensure_ascii=False, indent=2)
            reset_tasks += 1
            
            # Also need to reset the main manifest status if it's past 'chunked'
            main_manifest_path = f.replace('_chunks.json', '.json')
            if os.path.exists(main_manifest_path):
                with open(main_manifest_path, 'r', encoding='utf-8-sig') as mf:
                    main_data = json.load(mf)
                
                # If it's failed or merged, revert to chunked so stt_runner picks it up
                if main_data.get('status') in ['merged', 'failed', 'completed']:
                    main_data['status'] = 'chunked'
                    main_data.setdefault('steps', {})['stt'] = 'pending'
                    main_data['steps']['merge'] = 'pending'
                    
                    with open(main_manifest_path, 'w', encoding='utf-8-sig') as mf:
                        json.dump(main_data, mf, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error processing {f}: {e}")

print(f"Reset {reset_chunks} poisoned chunks across {reset_tasks} tasks.")

