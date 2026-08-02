import os

file_path = r'C:\Users\temp\.gemini\antigravity\brain\9ccc4726-3ac1-4fe6-bcb7-aa2c09335f30\implementation_plan.md'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old_row = "| **4 (已作廢)** | 第 5 點：繞過 Google 免費金鑰帳單 | **作廢/已測試失敗** | ⚪ **無效** | 經測試確認：Google Gemini API 限制 inlineData 檔案大小上限為 20MB。12分鐘 WAV (約 23MB) 必然被拒絕，因此強制綁定 File API 是唯一解，此方案徹底作廢。 |"

new_row = "| **4 (架構翻新)** | 第 5 點：繞過 Google 免費金鑰帳單 (縮短切片+InlineData) | **規劃中** | 🟡 **中** | 縮減音訊切片長度至 7 分鐘 (420 秒)，使 16kHz WAV 落在約 13.5MB (Base64 約 18MB)，完美合規 Google 的 20MB 上限，徹底擺脫 File API 依賴。 |"

if old_row in content:
    content = content.replace(old_row, new_row)
else:
    print("Could not find old row to replace.")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
