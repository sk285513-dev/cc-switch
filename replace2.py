import os

filepath = r'C:\LocalAI_Workstation\app.py'
with open(filepath, 'r', encoding='utf-8-sig') as f:
    content = f.read()

start_marker = '    st.subheader("2. 🔑 更換 Vertex AI 企業帳號與金鑰")'
end_marker = '    st.subheader("4. 📊 查詢 Google Cloud 帳務與授權資訊")'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx)

if start_idx == -1 or end_idx == -1:
    print('Error: Could not find markers.')
    exit(1)

replacement = '''    st.subheader("2. 🔑 更換 Vertex AI 企業帳號與金鑰")
    current_project = ""
    current_enterprise_account = ""
    if os.path.exists(CONFIG_PATH_LOCAL):
        try:
            import yaml
            with open(CONFIG_PATH_LOCAL, "r", encoding="utf-8-sig") as f:
                cfg = yaml.safe_load(f)
                current_project = cfg.get("api", {}).get("vertexai_project", "")
                current_enterprise_account = cfg.get("api", {}).get("gemini_api_account", "")
        except:
            pass
            
    st.markdown(f"**📊 狀態：** 目前綁定之企業帳號：{current_enterprise_account if current_enterprise_account else '尚未設定'}")
    
    with st.form("add_enterprise_key_form", clear_on_submit=False):
        ent_account = st.text_input("綁定的 Google 帳號 (明碼)", value=current_enterprise_account, placeholder="例如: admin@company.com")
        project_id = st.text_input("Google Cloud 專案 ID", value=current_project)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("💾 儲存企業帳號與專案 ID"):
                update_yaml_value(CONFIG_PATH_LOCAL, "vertexai_project", project_id.strip())
                
                # Update account safely
                try:
                    with open(CONFIG_PATH_LOCAL, "r", encoding="utf-8-sig") as f:
                        cfg_temp = yaml.safe_load(f) or {}
                except:
                    cfg_temp = {}
                    
                if "api" not in cfg_temp:
                    cfg_temp["api"] = {}
                cfg_temp["api"]["gemini_api_account"] = ent_account.strip()
                
                with open(CONFIG_PATH_LOCAL, "w", encoding="utf-8-sig") as f:
                    yaml.dump(cfg_temp, f, default_flow_style=False, allow_unicode=True)
                    
                st.success(f"✅ 企業帳號與專案 ID 已更新！")
                
        with col2:
            if st.form_submit_button("🚀 啟動 ADC 授權登入 (gcloud)"):
                import subprocess
                gcloud_cmd = r"C:\LocalAI_Workstation\gcloud_sdk\google-cloud-sdk\bin\gcloud.cmd"
                if os.path.exists(gcloud_cmd):
                    try:
                        subprocess.Popen([gcloud_cmd, "auth", "application-default", "login"], creationflags=subprocess.CREATE_NEW_CONSOLE)
                        if project_id:
                            subprocess.Popen([gcloud_cmd, "auth", "application-default", "set-quota-project", project_id], creationflags=subprocess.CREATE_NEW_CONSOLE)
                        st.success("✅ 已經開啟終端機與瀏覽器進行 ADC 登入！")
                    except Exception as e:
                        st.error(f"執行失敗: {e}")
                else:
                    st.error("找不到 gcloud 工具，請確認安裝路徑。")
                    
    st.divider()
    
    st.subheader("3. 💰 管理 Gemini 免費金鑰池 (keys.yaml)")
    st.caption("請先輸入您的 Google 帳號，再將金鑰分別貼入下方密碼框。系統將自動與帳號綁定並安全疊加。")
    try:
        import sys
        if r"C:\\LocalAI_Workstation" not in sys.path:
            sys.path.append(r"C:\\LocalAI_Workstation")
        from utils.key_manager import KeyManager
    except ImportError:
        KeyManager = None

    if KeyManager:
        loaded_keys = KeyManager.load_keys()
    else:
        loaded_keys = []
        st.error("無法載入 KeyManager 模組！")
        
    # 計算各帳號的金鑰數量
    account_counts = {}
    for k in loaded_keys:
        acc = k.get("account", "未綁定帳號")
        if not acc:
            acc = "未綁定帳號"
        if acc not in account_counts:
            account_counts[acc] = 0
        account_counts[acc] += 1
        
    st.markdown(f"**📊 狀態：** 目前免費金鑰池共安全持有 **{len(loaded_keys)}** 把金鑰。")
    if account_counts:
        for acc, count in account_counts.items():
            st.markdown(f"- {acc}: {count} 把")

    with st.form("add_free_key_12_form", clear_on_submit=True):
        st.markdown("##### ➕ 新增金鑰 (最多可同時輸入 12 把)")
        account_val = st.text_input("綁定的 Google 帳號 (明碼)", placeholder="例如: yourname@gmail.com")
        
        # 動態產生 12 個靜態綁定的密碼框，保證不當機
        new_keys_inputs = []
        for i in range(1, 13):
            val = st.text_input(f"API Key {i}", type="password", key=f"vault_key_{i}", placeholder="若無則留空")
            new_keys_inputs.append(val)
            
        if st.form_submit_button("💾 綁定並新增至金鑰池"):
            if not account_val.strip():
                st.error("❌ 請務必輸入綁定的 Google 帳號！")
            else:
                import datetime
                added_count = 0
                existing_values = [k.get("value") for k in loaded_keys]
                
                for k in new_keys_inputs:
                    k_clean = k.strip()
                    if k_clean and k_clean not in existing_values:
                        new_key_obj = {
                            "active": True,
                            "account": account_val.strip(),
                            "value": k_clean,
                            "added_date": datetime.date.today().isoformat(),
                            "expiry_date": "",
                            "notes": "Added via Dashboard UI"
                        }
                        loaded_keys.append(new_key_obj)
                        added_count += 1
                
                if added_count > 0:
                    if KeyManager:
                        success = KeyManager.save_keys(loaded_keys)
                        if success:
                            st.success(f"✅ 成功綁定 {account_val.strip()} 並匯入 {added_count} 把新金鑰！")
                            import time
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.error("❌ 寫入 keys.yaml 發生錯誤！")
                    else:
                        st.error("找不到 KeyManager，無法寫入。")
                else:
                    st.info("ℹ️ 未偵測到新金鑰，或金鑰已存在於池中。")

'''

new_content = content[:start_idx] + replacement + content[end_idx:]

with open(filepath, 'w', encoding='utf-8-sig') as f:
    f.write(new_content)

print('Success: Replaced section 2 and 3.')
