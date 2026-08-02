import os
import sys
from pathlib import Path

def register():
    script_dir = Path(__file__).parent.resolve()
    workspace_root = script_dir.parent
    run_workflow_py = workspace_root / "scripts" / "run_workflow.py"
    
    # 1. 取得 Windows 使用者開機啟動目錄
    appdata = os.environ.get("APPDATA")
    if not appdata:
        print("❌ 找不到 APPDATA 環境變數，無法註冊開機啟動。")
        return False
        
    startup_dir = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    if not startup_dir.exists():
        print(f"❌ 找不到啟動目錄: {startup_dir}")
        return False
        
    # 2. 建立 .bat 啟動指令檔
    bat_path = startup_dir / "run_legal_ai_workflow.bat"
    
    python_exe = sys.executable
    bat_content = f"""@echo off
title 臺灣法律教材長影音處理工作流 (Background Watcher)
echo 正在啟動法律影音處理監控服務...
cd /d "{workspace_root}"
"{python_exe}" "{run_workflow_py}"
pause
"""
    
    try:
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)
        print(f"✅ 成功註冊開機自啟動！已建立批次檔：\n   {bat_path}")
        return True
    except Exception as e:
        print(f"❌ 寫入啟動檔失敗: {e}")
        return False

if __name__ == "__main__":
    register()
