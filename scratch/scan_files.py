import os
from pathlib import Path

DRIVES = ['H:/', 'J:/']
REQUIRED_FOLDERS = [
    "強制執行法A", "強制執行法B", "票據法", "智慧財產權法", "稅法", "土地稅法", "土地法規",
    "土地登記", "不動產估價", "立法程序與技術", "法院組織法", "家事事件法115",
    "海商法與海洋法", "勞動社會法", "關稅法規", 
    "憲法", "民法", "身分法", "刑法", "行政法", "程序法", "民事訴訟法", "刑事訴訟法", "家事事件法", "民訴", "刑訴", "家事", "土地法", "商事法", "公司法", "證交法", "證券交易法"
]

all_files = []
for drive in DRIVES:
    if not os.path.exists(drive): continue
    for root, dirs, files in os.walk(drive):
        # Only process if any required folder name is in the path
        if not any(req in root for req in REQUIRED_FOLDERS):
            continue
        
        for f in files:
            if f.endswith('.mp4') or f.endswith('.wav'):
                if f.startswith('temp_extract_') or 'bandicam' in root.lower() or 'bandicam' in f.lower():
                    continue
                full_path = os.path.join(root, f)
                all_files.append(full_path)

print(f"Total valid media files found in allowed folders: {len(all_files)}")
