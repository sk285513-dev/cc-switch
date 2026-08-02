import codecs

path = r'C:\Users\temp\.gemini\antigravity\brain\e6fcb001-67fa-4006-bd69-8e5649678c85\LexMind_Omni_v5.1_Plan_Reviewed.md'
with codecs.open(path, 'r', 'utf-8') as f:
    content = f.read()

old_mermaid = '''mindmap
  root((LexMind-Omni<br/>法律實務 AI 工作站))
    原材料物流_前端
      [自動巡視與吸教材]<br/>auto_ingest_bot.py
      [批次題庫訓練]<br/>batch_exam_trainer.py
      [防重複過濾器]<br/>duplicate_guard.py
    加工管線_中樞
      [總管線控制器]<br/>run_workflow.py
      [媒體前置處理]<br/>preprocess_media.py
      [語音轉寫引擎]<br/>stt_runner.py
      [排版與圖表融合]<br/>markdown_formatter.py
    知識庫與檢索_後端
      [向量知識庫建立]<br/>law_digester.py
      [RAG 檢索顧問]<br/>rag_case_consultant.py
    金鑰與穩定_守護神
      [金鑰保險箱]<br/>quota_manager.py / vault.py
      [自動重啟與排錯]<br/>sre_watchdog.py / check_stuck.py
    全域共享模組_Domain
      [領域防護與國考規則大腦]<br/>national_exam_rules.py
    介面與交互_終端
      [戰情儀表板]<br/>app.py / settings_view.py'''

new_mermaid = '''mindmap
  root("LexMind-Omni 法律實務 AI 工作站")
    原材料物流_前端
      n1("[自動巡視與吸教材] auto_ingest_bot.py")
      n2("[批次題庫訓練] batch_exam_trainer.py")
      n3("[防重複過濾器] duplicate_guard.py")
    加工管線_中樞
      n4("[總管線控制器] run_workflow.py")
      n5("[媒體前置處理] preprocess_media.py")
      n6("[語音轉寫引擎] stt_runner.py")
      n7("[排版與圖表融合] markdown_formatter.py")
    知識庫與檢索_後端
      n8("[向量知識庫建立] law_digester.py")
      n9("[RAG 檢索顧問] rag_case_consultant.py")
    金鑰與穩定_守護神
      n10("[金鑰保險箱] quota_manager.py / vault.py")
      n11("[自動重啟與排錯] sre_watchdog.py / check_stuck.py")
    全域共享模組_Domain
      n12("[領域防護與國考規則大腦] national_exam_rules.py")
    介面與交互_終端
      n13("[戰情儀表板] app.py / settings_view.py")'''

content = content.replace(old_mermaid, new_mermaid)

with codecs.open(path, 'w', 'utf-8') as f:
    f.write(content)

print("Mermaid diagram fixed.")
