with open('src/App.tsx', 'r', encoding='utf-8') as f:
    app_content = f.read()

with open('server.ts', 'r', encoding='utf-8') as f:
    server_content = f.read()

# Let's search for "初始化" in both files
for i, line in enumerate(app_content.splitlines(), 1):
    if '初始化' in line:
        print(f"App.tsx:{i}: {line}")

for i, line in enumerate(server_content.splitlines(), 1):
    if '初始化' in line:
        print(f"server.ts:{i}: {line}")
