import os
import json
import tempfile
import streamlit as st
import sys
sys.path.insert(0, "C:\\LocalAI_Workstation")
from utils.config_manager import load_settings, save_settings, CONFIG_PATH, DEFAULT_CONFIG
import utils.config_manager as _cm
from utils.key_manager import KeyManager

def test_config_lifecycle():
    print("Running Sandbox Test: Config Manager")

    # 用臨時目錄隢離，不編接任何生產檔案
    with tempfile.TemporaryDirectory() as tmpdir:
        test_cfg_path = os.path.join(tmpdir, "config.yaml")
        test_keys_path = os.path.join(tmpdir, "keys.yaml")
        
        _orig_path = _cm.CONFIG_PATH
        _orig_keys = KeyManager.KEYS_PATH
        
        _cm.CONFIG_PATH = test_cfg_path
        KeyManager.KEYS_PATH = test_keys_path
        
        # 建立初始的 config.yaml 以供正則表達式更新
        initial_cfg = {
            "stt_engine": "gemini",
            "merge_engine": "gemini",
            "gemini_model_high_accuracy": "gemini-2.5-flash",
            "vertexai_project": "",
            "stt_concurrency": 6,
            "theme": "light",
            "backup_frequency": "daily"
        }
        import yaml
        with open(test_cfg_path, 'w', encoding='utf-8-sig') as f:
            yaml.dump({"settings": initial_cfg}, f, default_flow_style=False)
            
        try:
            # 測試 1: 預設載入 (無檔案狀態)
            if "app_config" in st.session_state:
                del st.session_state["app_config"]

            config = load_settings()
            assert config == DEFAULT_CONFIG, "Load failed on empty config"
            assert st.session_state.app_config == DEFAULT_CONFIG, "Session state not synced on load"
            print("✅ Test 1 Passed: Default load successful.")

            # 測試 2: 儲存新設定
            new_config = DEFAULT_CONFIG.copy()
            new_config["stt_concurrency"] = 99
            new_config["backup_frequency"] = "never"

            success = save_settings(new_config)
            assert success, "Save settings returned False"

            # 驗證檔案是否正確寫入且編碼正確
            assert os.path.exists(test_cfg_path), "Config file not created"
            with open(test_cfg_path, 'r', encoding='utf-8-sig') as f:
                saved_data = yaml.safe_load(f)
            assert saved_data["settings"]["stt_concurrency"] == 99, "File data mismatch"
            assert st.session_state.app_config["stt_concurrency"] == 99, "Session state not updated on save"
            print("✅ Test 2 Passed: Save settings and file persistence successful.")

            # 測試 3: 重新載入
            del st.session_state["app_config"]
            loaded = load_settings()
            assert loaded["stt_concurrency"] == 99, "Reload failed to read from disk"
            print("✅ Test 3 Passed: Reload from disk successful.")

            print("\n🎉 All Config Manager tests passed.")
        finally:
            _cm.CONFIG_PATH = _orig_path  # 無論測試成否必定還原，不汙染生產環境
            KeyManager.KEYS_PATH = _orig_keys

if __name__ == "__main__":
    test_config_lifecycle()
