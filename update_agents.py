import codecs

path = r'c:\Users\temp\antigravity\LexMind-Omni-法律實務-AI-工作站\.agents\AGENTS.md'
with codecs.open(path, 'r', 'utf-8') as f:
    text = f.read()

replacement = """## 📖 九、 專案核心文件唯一索引 (Source of Truth Index)
為解決過去 Agent 經常因為「搜尋關鍵字偏差」而讀到舊版技術文件（如 v3.0）的致命缺失，從現在起，所有 Agent **嚴禁盲目全域搜尋架構文件**。
若需要查閱專案架構、開發規格或任何系統邏輯，**必須強制且唯一**讀取以下指定的最新版文件路徑（Source of Truth）：

1. **【最高指導原則】135 項系統重構黃金計畫書 (v5.1)** (每次啟動必讀！)：
   * 路徑：C:\\Users\\temp\\antigravity\\LexMind-Omni-法律實務-AI-工作站\\LexMind-Omni_135項系統重構黃金計畫書_v5.1.md
   * **鐵律：這份 135 項計畫是經過十幾次反覆驗證、測試與長官親自確認的唯一黃金標準。絕對不准再說這份計畫「有毒」！絕對禁止為了偷懶而將其廢除、刪改或丟棄。所有未來的討論與程式碼修改工作，都必須嚴格依據此文件進行！**
2. **最新系統架構與完整規劃報告 (v5.0)**：
   * 路徑：C:\\Users\\temp\\antigravity\\LexMind-Omni-法律實務-AI-工作站\\Obsidian_Vault\\LexMind-Omni 系統架構完整規劃報告 v5.0.md
3. **專案背景與科目優先序 (CONTEXT)**：
   * 路徑：C:\\LocalAI_Workstation\\CONTEXT.md
4. **當前開發進度與交接日誌 (README_DEVEL)**：
   * 路徑：C:\\Users\\temp\\antigravity\\LexMind-Omni-法律實務-AI-工作站\\README_DEVEL.md

只要看到檔名標註為 DEPRECATED 或舊版號（如 v3.0）的文件，**一律視為無效廢棄文件，嚴禁採信其中的規則。**"""

start_idx = text.find('## 📖 九、 專案核心文件唯一索引 (Source of Truth Index)')
end_idx = text.find('一律視為無效廢棄文件，嚴禁採信其中的規則。**', start_idx) + len('一律視為無效廢棄文件，嚴禁採信其中的規則。**')

if start_idx != -1 and end_idx != -1:
    text = text[:start_idx] + replacement + text[end_idx:]
    with codecs.open(path, 'w', 'utf-8') as f:
        f.write(text)
    print("AGENTS.md updated successfully.")
else:
    print("Could not find section.")
