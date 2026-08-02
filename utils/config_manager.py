import os
import re
import yaml
import streamlit as st
from utils.key_manager import KeyManager

CONFIG_PATH = r"C:\LocalAI_Workstation\config.yaml"
KEYS_PATH = r"C:\LocalAI_Workstation\config\keys.yaml"

# 預設值回退
DEFAULT_CONFIG = {
    "stt_engine": "gemini",
    "merge_engine": "gemini",
    "gemini_model_high_accuracy": "gemini-2.5-flash",
    "vertexai_project": "",
    "stt_concurrency": 6,
    "ui_language": "zh_TW",
    "gemini_keys": []
}

def load_settings():
    """從 config.yaml 與 keys.yaml 載入設定，並同步至 session_state"""
    app_config = DEFAULT_CONFIG.copy()
    
    # 讀取 config.yaml
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8-sig') as f:
                cfg = yaml.safe_load(f)
                
            if cfg and "settings" in cfg:
                app_config["stt_engine"] = cfg["settings"].get("stt_engine", app_config["stt_engine"])
                app_config["merge_engine"] = cfg["settings"].get("merge_engine", app_config["merge_engine"])
                app_config["vertexai_project"] = cfg["settings"].get("vertexai_project", app_config["vertexai_project"])
                app_config["stt_concurrency"] = cfg["settings"].get("stt_concurrency", app_config["stt_concurrency"])
                
            if cfg and "api" in cfg:
                app_config["gemini_model_high_accuracy"] = cfg["api"].get("gemini_model_high_accuracy", app_config["gemini_model_high_accuracy"])
        except Exception as e:
            st.error(f"讀取 config.yaml 失敗: {e}")

    # 讀取 keys.yaml
    app_config["gemini_keys"] = KeyManager.load_keys()
            
    # 寫入 Session State
    if "app_config" not in st.session_state:
        st.session_state.app_config = app_config
    else:
        st.session_state.app_config.update(app_config)

    return app_config

def update_config_regex(key, new_value):
    """使用正則表達式更新 config.yaml，不破壞註解"""
    if not os.path.exists(CONFIG_PATH):
        return False
        
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
            content = f.read()

        # 支援字串(帶引號)、布林值與數字
        if isinstance(new_value, bool):
            value_str = "true" if new_value else "false"
            pattern = rf'^(\s*){key}:\s*([0-9]+|true|false|"[^"]*"|\'[^\']*\')'
            replacement = rf'\1{key}: {value_str}'
        elif isinstance(new_value, int):
            pattern = rf'^(\s*){key}:\s*([0-9]+|true|false|"[^"]*"|\'[^\']*\')'
            replacement = rf'\1{key}: {new_value}'
        else:
            pattern = rf'^(\s*){key}:\s*([0-9]+|true|false|"[^"]*"|\'[^\']*\')'
            replacement = rf'\1{key}: "{new_value}"'

        # 如果 pattern 沒有找到，則可能是原本沒有該設定。這裡為了簡單，假設該設定存在。
        # 如果未來需要，可加入 appending logic。
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        with open(CONFIG_PATH, "w", encoding="utf-8-sig") as f:
            f.write(new_content)
        return True
    except Exception as e:
        print(f"Error updating regex config: {e}")
        return False

def save_settings(new_config):
    """保存設定至 config.yaml 與 keys.yaml 並更新 session_state"""
    
    # 更新 config.yaml 中的欄位
    update_config_regex("stt_engine", new_config.get("stt_engine", "gemini"))
    update_config_regex("merge_engine", new_config.get("merge_engine", "gemini"))
    update_config_regex("gemini_model_high_accuracy", new_config.get("gemini_model_high_accuracy", "gemini-2.5-flash"))
    update_config_regex("vertexai_project", new_config.get("vertexai_project", ""))
    update_config_regex("stt_concurrency", new_config.get("stt_concurrency", 6))
    update_config_regex("vertexai_credentials_path", new_config.get("vertexai_credentials_path", "vertex_key.json"))
    
    # 寫入 keys.yaml
    if not KeyManager.save_keys(new_config.get("gemini_keys", [])):
        st.error("寫入 keys.yaml 失敗")
        return False
        
    # 更新 Session State
    if "app_config" not in st.session_state:
        st.session_state.app_config = new_config
    else:
        st.session_state.app_config.update(new_config)
        
    return True
