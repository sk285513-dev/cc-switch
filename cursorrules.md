# LexMind-Omni 專案 Cursor 規則

## 專案概述
本專案為台灣法律教材長影音自動轉譯工作站，將法律課程 MP4 轉換為 Markdown 講義、SRT 字幕與 RAG 索引。

## 技術棧
- **後端**：Python 3.10+，FastAPI / Streamlit
- **STT**：Gemini 2.5 Flash（主力雲端）+ Whisper（本地蒸餾輔助）
- **儲存**：A 碟（快取）、J 碟（原始影片 + 備份）
- **向量庫**：Qdrant（本地 Docker）

## 核心規則
1. STT 主力永遠使用 Gemini 雲端，禁止 Whisper 成為主輸出
2. 所有檔案使用 UTF-8 編碼
3. 法律術語必須精準（民法、刑法、行政法、土地登記等）
4. 新代理人進入必須先讀 README_DEVEL.md

## 目錄結構
```
scripts/          核心流水線腳本
config/           API 金鑰與設定
A:\chunks\        音訊切片暫存（完成後清理）
A:\manifests\     任務狀態 JSON
A:\processed_md\  最終成品輸出
A:\logs\          系統日誌
```

## 編碼慣例
- 所有 Python 腳本開頭加 `# -*- coding: utf-8 -*-`
- log 函數使用 `log_workflow()` / `log_error()`
- manifest 狀態：queued → stt → merge → formatter → completed
