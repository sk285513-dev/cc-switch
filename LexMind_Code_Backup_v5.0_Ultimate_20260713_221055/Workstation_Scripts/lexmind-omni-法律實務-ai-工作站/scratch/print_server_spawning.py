with open('server.ts', 'r', encoding='utf-8') as f:
    content = f.read().splitlines()

for idx in range(2010, 2032):
    print(f"{idx}: {content[idx - 1]}")
