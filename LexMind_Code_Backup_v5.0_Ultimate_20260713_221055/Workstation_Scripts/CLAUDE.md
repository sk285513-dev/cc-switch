# LexMind-Omni AI 協作規則 (CLAUDE.md)

本文件定義 AI 代理人在此專案工作時的行為準則。

## 必讀順序
1. 先讀 `README_DEVEL.md`（當前進度與架構）
2. 再讀 `.agents/AGENTS.md`（品質標準）
3. 再讀本文件

## 核心行為規則

### 絕對禁止
- ❌ 禁止未讀 README_DEVEL.md 就修改 scripts/ 下的腳本
- ❌ 禁止使用 Whisper 作為 STT 主力輸出
- ❌ 禁止在刪除操作前未先確認目標路徑不為空字串
- ❌ 禁止重複啟動已在背景運行的流水線任務

### 必須遵守
- ✅ 切換帳號時不能停止背景工作（watchdog 必須持續運行）
- ✅ 所有文字輸出使用 UTF-8 編碼
- ✅ 法律術語必須精準（不得有同音錯字）
- ✅ 每完成一個 chunk 立刻存檔（防止重複消耗 API）
- ✅ 刪除操作前必須先列印將刪除的檔案清單確認

## 安全操作規範

### 刪除前必做
```python
# 永遠先確認 path 不是空字串或根目錄
assert str(target_dir) not in ['', '.', '/', 'C:\\', 'C:\\LocalAI_Workstation']
print('將刪除:', list(target_dir.iterdir()))
# 等待確認後再執行
```

### manifest course_dir 修復
目前所有 manifest 的 `course_dir` 欄位為空，需補全：
- 格式：`J:\<科目>\<ch_N>\`
- 執行前先驗證路徑存在

## 流水線狀態機
```
queued → preprocess → chunk_planner → stt → merge → formatter → completed
                                       ↑ 失敗時重置回 pending
```
