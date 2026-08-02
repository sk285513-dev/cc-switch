import os
import yaml

filepath = r'C:\LocalAI_Workstation\app.py'
with open(filepath, 'r', encoding='utf-8-sig') as f:
    content = f.read()

start_marker = '    st.subheader("2. 🔑 更換 Vertex AI 企業帳號與金鑰")'
end_marker = '    st.divider()\n    \n    st.subheader("3. 💰 管理 Gemini 免費金鑰池 (keys.yaml)")'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx)

if start_idx == -1 or end_idx == -1:
    print('Error: Could not find markers.')
    exit(1)

replacement = '''    st.subheader("2. 🔑 更換 Vertex AI 企業帳號與金鑰")
    current_project = ""
    current_enterprise_account = ""
    current_project_name = ""
    current_project_number = ""
    
    if os.path.exists(CONFIG_PATH_LOCAL):
        try:
            with open(CONFIG_PATH_LOCAL, "r", encoding="utf-8-sig") as f:
                cfg = yaml.safe_load(f) or {}
                api_cfg = cfg.get("api", {})
                current_project = api_cfg.get("vertexai_project", "")
                current_enterprise_account = api_cfg.get("gemini_api_account", "")
                current_project_name = api_cfg.get("vertexai_project_name", "")
                current_project_number = api_cfg.get("vertexai_project_number", "")
        except:
            pass
            
    # 安全遮蔽專案 ID
    masked_project = "尚未設定"
    if current_project:
        if len(current_project) > 4:
            masked_project = current_project[:4] + "*" * (len(current_project) - 4)
        else:
            masked_project = "***"
            
    # 狀態列
    st.markdown(f"**📊 狀態：** 目前綁定之企業帳號：{current_enterprise_account if current_enterprise_account else '尚未設定'} | 專案名稱：{current_project_name if current_project_name else '未命名'} | 專案 ID：{masked_project}")
    
    with st.form("add_enterprise_key_form", clear_on_submit=False):
        ent_account = st.text_input("綁定的企業 Google 帳號 (明碼) [強烈建議填寫]", value=current_enterprise_account, placeholder="例如: admin@company.com (讓您記得這個專案是用哪個帳號申請的)")
        ent_project_name = st.text_input("專案名稱 (Project Name) [選填]", value=current_project_name, placeholder="使用者自訂的中文或英文名稱 (僅供記憶)")
        
        # 專案 ID 加入 type="password" 以策安全
        project_id = st.text_input("專案 ID (Project ID) [🔥 必填：上雲端授權必須要這個]", value=current_project, type="password", placeholder="英文與連字號組成的編號，或是 project 開頭的編號 (例如: my-project-123)")
        ent_project_number = st.text_input("專案數字編號 (Project Number) [選填]", value=current_project_number, placeholder="純阿拉伯數字的系統編號 (例如: 123456789012)")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("💾 儲存企業帳號與專案資訊"):
                # Update account safely
                try:
                    with open(CONFIG_PATH_LOCAL, "r", encoding="utf-8-sig") as f:
                        cfg_temp = yaml.safe_load(f) or {}
                except:
                    cfg_temp = {}
                    
                if "api" not in cfg_temp:
                    cfg_temp["api"] = {}
                    
                cfg_temp["api"]["gemini_api_account"] = ent_account.strip()
                cfg_temp["api"]["vertexai_project_name"] = ent_project_name.strip()
                cfg_temp["api"]["vertexai_project"] = project_id.strip()
                cfg_temp["api"]["vertexai_project_number"] = ent_project_number.strip()
                
                with open(CONFIG_PATH_LOCAL, "w", encoding="utf-8-sig") as f:
                    yaml.dump(cfg_temp, f, default_flow_style=False, allow_unicode=True)
                    
                st.success(f"✅ 企業帳號與專案資訊已更新！")
                import time
                time.sleep(1.0)
                st.rerun()  # 強制重新整理畫面，讓狀態列立刻更新！
                
        with col2:
            if st.form_submit_button("🚀 啟動 ADC 授權登入 (gcloud)"):
                if not project_id.strip():
                    st.error("❌ 啟動失敗：【專案 ID (Project ID)】為必填欄位，請先填寫並儲存。")
                else:
                    import subprocess
                    gcloud_cmd = r"C:\\LocalAI_Workstation\\gcloud_sdk\\google-cloud-sdk\\bin\\gcloud.cmd"
                    if os.path.exists(gcloud_cmd):
                        try:
                            subprocess.Popen([gcloud_cmd, "auth", "application-default", "login"], creationflags=subprocess.CREATE_NEW_CONSOLE)
                            subprocess.Popen([gcloud_cmd, "auth", "application-default", "set-quota-project", project_id.strip()], creationflags=subprocess.CREATE_NEW_CONSOLE)
                            st.success("✅ 已經開啟終端機與瀏覽器進行 ADC 登入！")
                        except Exception as e:
                            st.error(f"執行失敗: {e}")
                    else:
                        st.error("找不到 gcloud 工具，請確認安裝路徑。")
                        
'''

new_content = content[:start_idx] + replacement + content[end_idx:]

with open(filepath, 'w', encoding='utf-8-sig') as f:
    f.write(new_content)

print('Success: Replaced section 2 with security and rerun fixes.')
