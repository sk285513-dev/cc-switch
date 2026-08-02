import re

def build_tree(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    tree = []
    # Only keep structural UI elements
    pattern = re.compile(r'^(\s*)(with tab_|st\.subheader|st\.markdown\("#####|with st\.expander|st\.button|st\.columns|with col_|tab_.*st\.tabs)')
    
    for line_num, line in enumerate(lines):
        match = pattern.search(line)
        if match:
            indent = len(match.group(1))
            content = line.strip()
            # clean up content
            content = re.sub(r'st\.markdown\("#####(.*)"\)', r'Section: \1', content)
            content = re.sub(r'st\.subheader\("(.*)"\)', r'Subheader: \1', content)
            content = re.sub(r'st\.button\("(.*)".*\)', r'Button: \1', content)
            tree.append(f"{' ' * (indent // 4)}{content}")

    with open("C:/LocalAI_Workstation/architecture_tree.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(tree))
    print("Tree generated!")

if __name__ == "__main__":
    build_tree("C:/LocalAI_Workstation/app.py")
