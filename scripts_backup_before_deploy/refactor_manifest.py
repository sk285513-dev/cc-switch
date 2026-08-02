import re

def refactor_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Read manifest
    content = re.sub(
        r'with open\(([^,]+), \s*[\'"]r[\'"], \s*encoding=[\'"]utf-8[\'"]\)\s+as\s+\w+:\s+(\w+)\s*=\s*json\.load\([^)]+\)',
        r'with ManifestManager(\1) as mm:\n            \2 = mm.read()',
        content
    )

    # Write manifest
    content = re.sub(
        r'with open\(([^,]+), \s*[\'"]w[\'"], \s*encoding=[\'"]utf-8[\'"]\)\s+as\s+\w+:\s+json\.dump\(([^,]+),\s*[^,]+,\s*ensure_ascii=False,\s*indent=2\)',
        r'with ManifestManager(\1) as mm:\n            mm.write(\2)',
        content
    )

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

refactor_file(r'C:\LocalAI_Workstation\scripts\run_workflow.py')
refactor_file(r'C:\LocalAI_Workstation\scripts\markdown_formatter.py')
refactor_file(r'C:\LocalAI_Workstation\scripts\merge_transcript.py')
refactor_file(r'C:\LocalAI_Workstation\scripts\stt_runner.py')
print("Done")
