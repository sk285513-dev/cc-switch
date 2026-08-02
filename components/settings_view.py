import streamlit as st
import sys
import os
sys.path.insert(0, "C:\\LocalAI_Workstation")
from utils.config_manager import save_settings
from utils.key_manager import KeyManager
from utils.i18n import _

STRATEGIES = {
    "A": {"stt_engine": "gemini", "merge_engine": "gemini"},
    "B": {"stt_engine": "gemini", "merge_engine": "vertexai"},
    "C": {"stt_engine": "gemini", "merge_engine": "vertexai"},
    "D": {"stt_engine": "local_whisper", "merge_engine": "gemini"},
    "E": {"stt_engine": "vertexai", "merge_engine": "vertexai"}
}

def get_strategy_id(config):
    stt = config.get("stt_engine", "gemini")
    merge = config.get("merge_engine", "gemini")
    for s_id, s_config in STRATEGIES.items():
        if s_config["stt_engine"] == stt and s_config["merge_engine"] == merge:
            return s_id
    return "A"  # Default

def render_settings_page():
    st.markdown(f"## ⚙️ {_('企業級架構與金鑰池設定介面')}")
    st.caption(_("此頁面完全取代舊版 setup_wizard.py，直接寫入 config.yaml 與 keys.yaml。"))
    
    config = st.session_state.get("app_config", {})
    
    # removed st.form
    st.subheader(f"1. 🎯 {_('核心處理策略 (Strategy Matrix)')}")
    current_strategy = get_strategy_id(config)
    strategy_options = [
        "A - " + _("純個人帳號 雲端免費金鑰池流 (0成本)"),
        "B - " + _("混合雙打: STT免費池 + 精校 Vertex AI (無折抵金/鎖Flash)"),
        "C - " + _("混合雙打: STT免費池 + 精校 Vertex AI (有折抵金解封Pro)"),
        "D - " + _("本地無須雲端免費金鑰池流: 本機 Whisper + AI Studio"),
        "E - " + _("全 Vertex 企業級通道 (極度昂貴)")
    ]
    strat_index = ["A", "B", "C", "D", "E"].index(current_strategy)
    selected_strategy_str = st.radio(_("選擇系統策略路徑"), options=strategy_options, index=strat_index)
    selected_strategy = selected_strategy_str[0] # 取 A, B, C, D, E

    st.subheader(f"2. 💰 {_('管理 Gemini 免費金鑰池 (keys.yaml)')}")
    
    # Backup and Restore UI
    st.caption(_("🔐 安全防護：自動備份與還原"))
    cols = st.columns([2, 1])
    with cols[0]:
        backups = KeyManager.get_backup_list()
        if backups:
            selected_backup = st.selectbox(_("選擇欲還原的歷史備份 (依時間排序)"), backups)
        else:
            st.selectbox(_("無歷史備份記錄"), ["無"])
            selected_backup = None
    with cols[1]:
        st.write("")
        st.write("")
        if selected_backup and st.button(_("🔄 從選取備份還原")):
            if KeyManager.restore_backup(selected_backup):
                st.success(_("還原成功！請重新整理以套用。"))
            else:
                st.error(_("還原失敗！"))

    gemini_keys = config.get("gemini_keys", [])
    if not isinstance(gemini_keys, list):
        gemini_keys = []
        
    st.markdown(f"#### 📊 {_('金鑰彈藥庫戰情看板')}")
    total_keys = len(gemini_keys)
    # 如果是字串格式代表舊版預設啟用，若是 dict 則看 active 欄位
    active_keys = sum(1 for k in gemini_keys if (isinstance(k, dict) and k.get("active", False)) or isinstance(k, str))
    inactive_keys = total_keys - active_keys
    
    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric("📦 總金鑰數", total_keys)
    metric_col2.metric("🟢 有效/啟用中", active_keys)
    metric_col3.metric("🔴 失效/已停用", inactive_keys)
    st.divider()

    st.info(_("您可以在此批次貼上混雜的原始資料，系統將自動萃取並合併有效金鑰："))
    raw_input = st.text_area(_("在此貼上原始金鑰資料..."), height=100)
    
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    with col_btn1:
        parse_clicked = st.button(_("🔄 1. 解析原始資料並合併至下方表格"))
    with col_btn2:
        test_clicked = st.button(_("🚀 2. 啟動全體金鑰檢測 (自動過濾 401/403 停權)"))
    with col_btn3:
        clean_clicked = st.button(_("🗑️ 3. 一鍵清理 401/403 死金鑰"))

    st.info(_("請在下方表格中管理您的金鑰，可填寫對應帳號與註記，並透過 Active 開關啟用或停用。"))
        
    if parse_clicked and raw_input.strip():
        parsed_keys = KeyManager.parse_raw_text(raw_input)
        if parsed_keys:
            existing_values = {k.get("value") if isinstance(k, dict) else k for k in gemini_keys}
            added = 0
            for pk in parsed_keys:
                if pk.get("value") not in existing_values:
                    gemini_keys.append(pk)
                    existing_values.add(pk.get("value"))
                    added += 1
            if added > 0:
                st.success(f"已成功解析並合併 {added} 把新金鑰！請在下方表格確認，並點擊最下方「儲存並套用設定」。")
            else:
                st.info("匯入的金鑰都已存在於列表中。")
        else:
            st.warning("找不到任何有效的金鑰。")
            
    if test_clicked and gemini_keys:
        import asyncio
        import aiohttp
        st.info("開始非同步測試金鑰 (啟動 Token Bucket 限速)...")
        my_bar = st.progress(0)
        total = len(gemini_keys)
        
        async def check_key(session, semaphore, index, k):
            if isinstance(k, dict):
                val = k.get("value", "")
            else:
                val = k
            if not val:
                return index, k, "⚠️ 缺少金鑰", False
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={val}"
            async with semaphore:
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as res:
                        status = res.status
                        if status == 200:
                            return index, k, "✅ 狀態正常 (200)", True
                        elif status in [401, 403]:
                            return index, k, f"🔴 停權/無效 ({status})", False
                        elif status == 429:
                            return index, k, "⏳ 額度耗盡/限速 (429)", True 
                        else:
                            return index, k, f"⚠️ 未知 ({status})", True
                except asyncio.TimeoutError:
                    return index, k, "⚠️ 網路超時", True
                except Exception as e:
                    return index, k, "⚠️ 連線錯誤", True

        async def run_checks():
            semaphore = asyncio.Semaphore(3) # 限速：每秒最多 3 把 (防 WAF 429)
            async with aiohttp.ClientSession() as session:
                tasks = [check_key(session, semaphore, i, k) for i, k in enumerate(gemini_keys)]
                results = []
                completed = 0
                for f in asyncio.as_completed(tasks):
                    res = await f
                    results.append(res)
                    completed += 1
                    my_bar.progress(completed / total)
                return results

        # 建立全新的 event loop 防止 Streamlit 執行緒衝突
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            results = loop.run_until_complete(run_checks())
        finally:
            loop.close()
        
        for idx, k, status_str, is_active in results:
            if isinstance(k, dict):
                k["notes"] = status_str
                if not is_active:
                    k["active"] = False
            else:
                gemini_keys[idx] = {"account": "", "value": val, "active": is_active, "notes": status_str, "added_date": "", "expiry_date": ""}
                
        st.success("非同步測試完畢！狀態已更新至下方表格，請確認後點擊最下方「儲存並套用設定」。")
        
    if clean_clicked and gemini_keys:
        original_len = len(gemini_keys)
        # 【BUG 修正 2026-07-23】
        # 原本清理條件過嚴：active==False 且 notes 含 401/403 才清除
        # 但因為上方 BUG 導致 inactive 金鑰的 notes 從未被更新，永遠清不掉
        # 修正：只要 active==False 即視為失效金鑰，直接清除
        gemini_keys = [k for k in gemini_keys if not (
            isinstance(k, dict) and k.get("active") == False
        )]
        cleaned_count = original_len - len(gemini_keys)
        config["gemini_keys"] = gemini_keys
        st.success(f"已一鍵清除 {cleaned_count} 把停用金鑰！請點擊最下方「儲存並套用設定」。")
    formatted_keys = []
    import datetime
    for k in gemini_keys:
        if isinstance(k, dict):
            formatted_keys.append(k)
        elif isinstance(k, str):
            formatted_keys.append({
                "account": "",
                "value": k,
                "added_date": datetime.date.today().isoformat(),
                "expiry_date": "",
                "active": True
            })
            
    # 顯示 Data Editor
    edited_keys = st.data_editor(
        formatted_keys,
        num_rows="dynamic",
        width="stretch",
        column_config={
            "active": st.column_config.CheckboxColumn("啟用 (Active)", default=True),
            "account": st.column_config.TextColumn("帳號 (Account)"),
            "value": st.column_config.TextColumn("金鑰 (API Key)", required=True),
            "added_date": st.column_config.TextColumn("新增日期 (YYYY-MM-DD)"),
            "expiry_date": st.column_config.TextColumn("失效日期 (YYYY-MM-DD)"),
            "notes": st.column_config.TextColumn("狀態與備註 (Notes)")
        }
    )

    st.subheader(f"3. 🏢 {_('Vertex AI 企業專案設定')}")
    vertexai_project = st.text_input(_("Google Cloud 專案 ID (Project ID)"), value=config.get("vertexai_project") or "")
    
    st.subheader(f"4. 🚀 {_('背景工作緒與並發管理 (Concurrency Settings)')}")
    concurrency_mode = st.radio(_("並發模式設定"), [_("自動調適模式 (Adaptive, 推薦)"), _("強制多工併發 (Manual)"), _("安全單工模式 (Single-thread)")], index=0)
    
    if "Manual" in concurrency_mode or "強制" in concurrency_mode:
        stt_concurrency = st.slider(_("強制並發緒數目"), min_value=1, max_value=10, value=int(config.get("stt_concurrency") or 6))
    elif "Single" in concurrency_mode or "單工" in concurrency_mode:
        stt_concurrency = 1
        st.info(_("已鎖定為單工模式 (1 緒)，極度穩定但速度最慢。"))
    else:
        st.info(_("系統將會根據底層 KPI_TARGET 自動升降並發數 (預設基準為 6 緒)。"))
        stt_concurrency = int(config.get("stt_concurrency", 6))
        
    if stt_concurrency > 6:
        st.warning(_("⚠️ 高並發可能導致顯示卡過熱 (超過 78°C) 或藍白當機 (BSOD)；且依據實測，超過 10 緒極易引發 API 的 Thundering Herd (503) 封鎖風暴。請謹慎設定。"))

    st.subheader(f"5. 🤖 {_('Gemini 模型版本設定 (Model Setting)')}")
    st.caption(_("Google 的模型版本更新頻繁，您可以在此手動指定 API 欲呼叫的確切模型名稱 (例如 gemini-2.5-flash, gemini-1.5-pro)。"))
    gemini_model = st.text_input(_("Gemini 呼叫模型名稱"), value=config.get("gemini_model_high_accuracy") or "gemini-2.5-flash")

    st.subheader(f"6. {_('🌐 系統介面語言 (Language)')}")
    lang_options = {"zh_TW": _("繁體中文 (zh_TW)"), "en_US": _("英文 (en_US)")}
    current_lang = config.get("ui_language", "zh_TW")
    selected_lang_key = st.radio(_("🌐 系統介面語言 (Language)"), options=list(lang_options.keys()), format_func=lambda x: lang_options[x], index=0 if current_lang == "zh_TW" else 1, label_visibility="collapsed")

    submitted = st.button(_("儲存並套用設定"))
    
    if submitted:
        # Parse Keys
        new_keys = [k for k in edited_keys if k.get("value") and str(k.get("value")).strip()]
        
        # Apply Strategy
        new_config = STRATEGIES[selected_strategy].copy()
        new_config["gemini_keys"] = new_keys
        new_config["vertexai_project"] = vertexai_project
        new_config["stt_concurrency"] = stt_concurrency
        new_config["gemini_model_high_accuracy"] = gemini_model.strip()
        new_config["ui_language"] = selected_lang_key
        new_config["vertexai_credentials_path"] = config.get("vertexai_credentials_path", "vertex_key.json")
        
        if save_settings(new_config):
            st.success(_("設定已成功儲存！重新載入中..."))
        else:
            st.error(_("❌ 設定儲存失敗，請檢查權限。"))
            
    st.divider()
    if st.button(_("🔐 進行 Vertex AI 安全憑證登入 (gcloud auth login)")): 
        # 非同步觸發 gcloud 指令
        os.system('start cmd /c "C:\\LocalAI_Workstation\\gcloud_sdk\\google-cloud-sdk\\bin\\gcloud.cmd auth application-default login && pause"')
        st.success("已彈出終端機視窗引導您進行 ADC 安全登入！登入完成後即可關閉視窗。")

