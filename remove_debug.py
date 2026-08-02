lines = open('C:/LocalAI_Workstation/app.py', 'r', encoding='utf-8').readlines()
new_lines = [line for line in lines if "st.write(\"Initializing Agent...\")" not in line and "st.write(\"Agent initialized! Now loading init_docs...\")" not in line and "st.write(\"Upserting init_docs...\")" not in line]

with open('C:/LocalAI_Workstation/app.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
