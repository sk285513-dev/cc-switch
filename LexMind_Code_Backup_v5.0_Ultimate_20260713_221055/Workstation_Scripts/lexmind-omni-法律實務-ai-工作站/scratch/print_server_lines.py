with open('server.ts', 'r', encoding='utf-8') as f:
    content = f.read().splitlines()

for idx in range(2040, 2095):
    print(f"{idx}: {content[idx - 1]}")
