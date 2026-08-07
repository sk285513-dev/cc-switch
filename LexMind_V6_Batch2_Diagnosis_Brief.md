# LexMind V6 第二批核心腳本病灶診斷簡報 (Batch 2 Diagnosis Brief)

## 1. 系統當前狀態 (Current State)
* **第一批已收斂 (Batch 1 Completed)**: workflow_helper.py, manifest_manager.py, stt_runner.py, un_workflow.py 已經完成修復，並全數通過 21 個 [STAGE] 斷點系統實裝。狀態機與檔案鎖 (ManifestManager) 均已穩固。
* **第二批待修復 (Batch 2 Pending)**: 目標檔案為 markdown_formatter.py, quota_manager.py, merge_transcript.py, model_router.py。
* **外部警告信號**: 外部專家傳回了 2825e7e 提交紀錄，指出針對 quota_manager, merge_transcript, markdown_formatter 的修復中，存在**「壞補丁緊急警告 (Bad Patch Emergency Warning)」**。

## 2. 歷史殘留的「九條實戰病灶」
我們過去的紀錄指出，第二批檔案面臨的深層問題如下：
1. **markdown_formatter**: 逾時崩潰、缺乏斷點、收尾黑洞 (Wrap-up Blackhole)。
2. **model_router**: 備援退化、冷卻繞過、洗版 (Spamming logs)。
3. **quota_manager**: 路徑錨定錯誤、單例模式 (Singleton) 衝突、日誌編碼 (BOM JSONDecodeError) 問題。
4. **merge_transcript**: 引擎穿透、Map/Reduce 斷點缺失。

## 3. 診斷任務目標 (Debug Objective)
請專家次代理人 (Sub-agents) 根據第一批的《架構審查報告》與上述病灶特徵，深入盤點 scripts_v6/ 底下的這三支檔案 (quota_manager.py, merge_transcript.py, markdown_formatter.py)，找出外部專家警告的「壞補丁」陷阱是什麼？真正的問題根源又藏在哪裡？
