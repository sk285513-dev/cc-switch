import os

warnings = {
    1: '''# ==============================================================================
# [CRITICAL DEPENDENCY WARNING] Group 1: 領域防護與前端物流 (Ingestion & Rules)
# ------------------------------------------------------------------------------
# ⚠️ 此檔案屬於高度解耦架構的【Group 1】。
# 負責掃描、吸收及國考權重判定。修改評分標準或過濾邏輯時，必須同步檢查
# 相關檔案，以確保評分標準一致。
# 修改前請務必參閱：PIPELINE_DEPENDENCIES.md
# ==============================================================================
''',
    2: '''# ==============================================================================
# [CRITICAL DEPENDENCY WARNING] Group 2: 核心加工管線 (Core Pipeline)
# ------------------------------------------------------------------------------
# ⚠️ 此檔案屬於高度解耦架構的【Group 2】。
# 修改此檔案時，必須確保多執行緒併發 (Concurrency) 及跨進程 JSON 狀態寫入的安全。
# 任何資料輸出格式的變動，都會直接導致 Group 5 (UI) 與 Group 8 (KPI) 癱瘓！
# 修改前請務必參閱：PIPELINE_DEPENDENCIES.md
# ==============================================================================
''',
    3: '''# ==============================================================================
# [CRITICAL DEPENDENCY WARNING] Group 3: 金鑰安全與保險箱 (Security & Vault)
# ------------------------------------------------------------------------------
# ⚠️ 此檔案屬於高度解耦架構的【Group 3】。
# 負責 Vertex AI / Gemini 金鑰加密解密與 429 斷路器輪替。絕不可破壞此處的保護機制。
# 修改前請務必參閱：PIPELINE_DEPENDENCIES.md
# ==============================================================================
''',
    4: '''# ==============================================================================
# [CRITICAL DEPENDENCY WARNING] Group 4: 系統守門員與高可用 (SRE, Watchdog & Email)
# ------------------------------------------------------------------------------
# ⚠️ 此檔案屬於高度解耦架構的【Group 4】。
# 負責監控卡死並發送 SMTP Email 警報。嚴禁在除錯時閹割掉 Email 發送與監控邏輯。
# 修改前請務必參閱：PIPELINE_DEPENDENCIES.md
# ==============================================================================
''',
    5: '''# ==============================================================================
# [CRITICAL DEPENDENCY WARNING] Group 5: 前端介面與路由代理 (UI & Router)
# ------------------------------------------------------------------------------
# ⚠️ 此檔案屬於高度解耦架構的【Group 5】。
# 修改儀表板 UI 或顯示邏輯時，絕對必須同步更新 Group 9 (視覺測試機器人) 的截圖 OCR 辨識邏輯。
# 本儀表板讀取的資料來自 Group 1/2，若顯示異常，請勿擅自修改後端資料格式！
# 修改前請務必參閱：PIPELINE_DEPENDENCIES.md
# ==============================================================================
''',
    6: '''# ==============================================================================
# [CRITICAL DEPENDENCY WARNING] Group 6: 外部題庫與法規爬蟲 (External Crawlers)
# ------------------------------------------------------------------------------
# ⚠️ 此檔案屬於高度解耦架構的【Group 6】。
# 抓取下來的資料格式必須完全與本機 DB (Group 1/5) 的解析格式對齊。
# 修改前請務必參閱：PIPELINE_DEPENDENCIES.md
# ==============================================================================
''',
    7: '''# ==============================================================================
# [CRITICAL DEPENDENCY WARNING] Group 7: 系統圖表與報告匯出 (Export & Visualization)
# ------------------------------------------------------------------------------
# ⚠️ 此檔案屬於高度解耦架構的【Group 7】。
# 修改前請務必參閱：PIPELINE_DEPENDENCIES.md
# ==============================================================================
''',
    8: '''# ==============================================================================
# [CRITICAL DEPENDENCY WARNING] Group 8: 系統啟動與本地工作站入口 (Startup & Entry)
# ------------------------------------------------------------------------------
# ⚠️ 系統最高入口點！絕對禁止 AI 擅自覆蓋、魔改或閹割這些啟動腳本。
# 修改前請務必參閱：PIPELINE_DEPENDENCIES.md
# ==============================================================================
''',
    9: '''# ==============================================================================
# [CRITICAL DEPENDENCY WARNING] Group 9: 視覺化自我糾錯與 UI 自動測試 (Vision UI Testers)
# ------------------------------------------------------------------------------
# ⚠️ 此檔案屬於高度解耦架構的【Group 9】。
# 負責自動截圖與 OCR 解讀儀表板。一旦 Group 5 的畫面佈局改變，這裡的座標與關鍵字必須同步更新。
# 修改前請務必參閱：PIPELINE_DEPENDENCIES.md
# ==============================================================================
'''
}

groups = {
    1: ['scripts_v6/national_exam_rules.py', 'scripts_v6/auto_ingest_bot.py', 'scripts_v6/batch_exam_trainer.py'],
    2: ['scripts_v6/run_workflow.py', 'scripts_v6/workflow_helper.py', 'scripts_v6/file_watcher.py', 'scripts_v6/preprocess_media.py', 'scripts_v6/chunk_planner.py', 'scripts_v6/stt_runner.py', 'scripts_v6/merge_transcript.py', 'scripts_v6/markdown_formatter.py', 'scripts_v6/visual_analyzer.py', 'scripts_v6/process_multimodal_file.py', 'scripts_v6/whisper_pool.py', 'scripts_v6/win32_kernel.py'],
    3: ['scripts_v6/quota_manager.py', 'scripts_v6/utils/vault.py', 'scripts_v6/utils/key_manager.py'],
    4: ['scripts_v6/sre_watchdog.py', 'scripts_v6/check_stuck.py', 'scripts_v6/auto_verify.py', 'scripts_v6/monitor_progress.py'],
    5: ['app.py', 'scripts_v6/ollama_router.py', 'scripts_v6/gemini_proxy.py'],
    6: ['C:/LocalAI_Workstation/bot_ultimate_real_crawler.py', 'C:/LocalAI_Workstation/bot_ultimate_600_crawler.py', 'C:/LocalAI_Workstation/bot_ultimate_hierarchy_crawler.py', 'C:/LocalAI_Workstation/law_scraper_cli.py'],
    7: ['scripts_v6/export_plan.py', 'scripts_v6/export_plan_api.py', 'scripts_v6/export_plan_png.py'],
    8: ['C:/LocalAI_Workstation/一鍵啟動三大監控視窗.ps1', 'C:/LocalAI_Workstation/LexMind一鍵啟動_終極版.ps1', 'C:/LocalAI_Workstation/dashboard_runner.ps1', 'C:/LocalAI_Workstation/kpi_runner.ps1'],
    9: ['C:/LocalAI_Workstation/bot_ultimate_tester.py', 'C:/LocalAI_Workstation/bot_pairwise_ui_tester.py', 'C:/LocalAI_Workstation/capture_streamlit.py', 'C:/LocalAI_Workstation/test_screenshot.py']
}

base_dir = 'C:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站'

for group_id, files in groups.items():
    warning_text = warnings[group_id]
    for file_path in files:
        if not file_path.startswith('C:/'):
            full_path = os.path.join(base_dir, file_path)
        else:
            full_path = file_path
        
        if os.path.exists(full_path):
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Avoid duplicate warnings
            if '[CRITICAL DEPENDENCY WARNING]' not in content:
                # For powershell, handle BOM or # encoding? # is safe anyway.
                new_content = warning_text + content
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Updated: {full_path}")
            else:
                print(f"Skipped (already has warning): {full_path}")
        else:
            print(f"File not found: {full_path}")
