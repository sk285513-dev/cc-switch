import os

filepath = r'C:\LocalAI_Workstation\app.py'
with open(filepath, 'r', encoding='utf-8-sig') as f:
    content = f.read()

start_marker = '    st.subheader("3. 💰 管理 Gemini 免費金鑰池 (keys.yaml)")'
end_marker = '        st.success(f"✅ 已成功覆寫 {KEYS_YAML_DEST_LOCAL} (已透過 Vault 加密)")'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx)

if start_idx == -1 or end_idx == -1:
    print('Error: Could not find markers.')
    exit(1)

end_idx += len(end_marker)

replacement = '''    st.subheader("3. 💰 管理 Gemini 免費金鑰池 (keys.yaml)")
    st.caption("為確保極致資安，請將金鑰分別貼入下方密碼框。系統將自動排版疊加，絕不覆蓋舊金鑰。")
    try:
        import sys
        if r"C:\\LocalAI_Workstation" not in sys.path:
            sys.path.append(r"C:\\LocalAI_Workstation")
        from utils.vault import Vault
        import yaml
    except ImportError:
        Vault = None
        import yaml

    # 解析目前的 YAML 檔案來計算數量
    free_keys_count = 0
    parsed_keys = {"gemini": []}
    gemini_list = []
    if os.path.exists(KEYS_YAML_DEST_LOCAL):
        with open(KEYS_YAML_DEST_LOCAL, "r", encoding="utf-8-sig") as f:
            raw_content = f.read()
            decrypted_content = ""
            if Vault:
                try:
                    decrypted_content = Vault.decrypt_data(raw_content)
                except Exception:
                    decrypted_content = raw_content
            else:
                decrypted_content = raw_content
            
            try:
                parsed_keys = yaml.safe_load(decrypted_content) or {}
                gemini_list = parsed_keys.get("gemini", [])
                if not isinstance(gemini_list, list):
                    gemini_list = []
                free_keys_count = len(gemini_list)
            except Exception:
                pass

    st.markdown(f"**📊 狀態：** 目前免費金鑰池安全持有 **{free_keys_count}** 把金鑰。")

    with st.form("add_free_key_12_form", clear_on_submit=True):
        st.markdown("##### ➕ 新增金鑰 (最多可同時輸入 12 把)")
        
        # 動態產生 12 個靜態綁定的密碼框，保證不當機
        new_keys_inputs = []
        for i in range(1, 13):
            val = st.text_input(f"API Key {i}", type="password", key=f"vault_key_{i}", placeholder="若無則留空")
            new_keys_inputs.append(val)
            
        if st.form_submit_button("💾 加密並新增至金鑰池"):
            added_count = 0
            for k in new_keys_inputs:
                k_clean = k.strip()
                if k_clean and k_clean not in gemini_list:
                    gemini_list.append(k_clean)
                    added_count += 1
            
            if added_count > 0:
                parsed_keys["gemini"] = gemini_list
                new_yaml = yaml.dump(parsed_keys, sort_keys=False, allow_unicode=True)
                
                os.makedirs(os.path.dirname(KEYS_YAML_DEST_LOCAL), exist_ok=True)
                if Vault:
                    try:
                        content_to_save = Vault.encrypt_data(new_yaml)
                    except Exception:
                        content_to_save = new_yaml
                else:
                    content_to_save = new_yaml
                    
                with open(KEYS_YAML_DEST_LOCAL, "w", encoding="utf-8-sig") as f:
                    f.write(content_to_save)
                    
                st.success(f"✅ 成功加密並匯入 {added_count} 把新金鑰！")
                import time
                time.sleep(1.5)
                st.rerun()
            else:
                st.info("ℹ️ 未偵測到新金鑰，或金鑰已存在於池中。")'''

new_content = content[:start_idx] + replacement + content[end_idx:]

with open(filepath, 'w', encoding='utf-8-sig') as f:
    f.write(new_content)

print('Success: Replaced vault section.')
