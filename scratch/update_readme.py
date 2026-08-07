import os
import re

file_path = "C:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/README_DEVEL.md"
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

old_text = "3. **完成靜態檔案導出**：為解決動態 Mermaid SVG 破圖問題，已開發專屬腳本透過 mermaid.ink 與 Base64 轉換，成功輸出無損的 HTML 與 PDF 版本至使用者的下載區，作為後續送交審查的 Payload。"

new_text = "3. **完成靜態檔案導出與 Playwright 地雷標記**：為解決動態 Mermaid SVG 破圖問題，已改用本地端 Playwright 無頭渲染，成功輸出無損的 HTML 與 PNG。\\n   * **【重要傳承】**：千萬別再用 mermaid.ink 等不穩定的外部 API！\\n   * **【Mermaid 11.x 地雷】**：新版 SVG 已移除 aria 屬性，截圖時只能用 page.wait_for_selector('svg')，否則會 Timeout！\\n   * **【節點冒號地雷】**：Mermaid 節點名稱中絕對禁止出現冒號 (:)，否則必定觸發 	.shape is not a function 崩潰。這些血淚教訓已正式寫入 AGENTS.md 第廿一條。"

text = text.replace(old_text, new_text)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)

print("Updated README_DEVEL.md successfully!")
