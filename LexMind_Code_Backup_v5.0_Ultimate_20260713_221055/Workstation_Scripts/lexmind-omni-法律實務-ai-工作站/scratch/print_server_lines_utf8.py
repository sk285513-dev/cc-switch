import sys

# Set output encoding to UTF-8
sys.stdout.reconfigure(encoding='utf-8')

with open('server.ts', 'r', encoding='utf-8') as f:
    content = f.read().splitlines()

for idx in range(2040, 2075):
    print(f"{idx}: {content[idx - 1]}")
