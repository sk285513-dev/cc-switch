try:
    import json
except ImportError:
    import json
import json
import glob
import os

manifest_dir = r'A:\manifests'
json_files = glob.glob(os.path.join(manifest_dir, '*.json'))
# Exclude chunks manifests
manifests = [f for f in json_files if not f.endswith('_chunks.json')]

completed_count = 0
poisoned = []
for f in manifests:
    try:
        with open(f, 'r', encoding='utf-8') as file:
            data = json.load(file)
            if data.get('status') == 'completed':
                completed_count += 1
                # Check if it has chunks_backup in F:\chunks_backup
                course_name = data.get('course_name')
                backup_path = os.path.join(r'F:\chunks_backup', course_name)
                if not os.path.exists(backup_path):
                    poisoned.append(course_name)
    except:
        pass

print(f"Total manifests: {len(manifests)}")
print(f"Total completed manifests: {completed_count}")
print(f"Poisoned (no F:\\ backup) among completed: {len(poisoned)}")
