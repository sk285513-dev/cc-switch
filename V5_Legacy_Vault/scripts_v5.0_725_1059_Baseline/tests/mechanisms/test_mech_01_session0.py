import os
import subprocess
import time
from pathlib import Path

def test_mechanism_01_session0_breakthrough(tmp_path: Path):
    """
    機制一：實體會話突破機制之設計 (Session 0 Breakthrough via VBS Isolation)
    嚴格遵循論文實作，使用 WScript.Shell 的 .Run(1, False) 發起非同步調用。
    """
    
    # 建立一個測試用的 mock 腳本，取代 bot_ultimate_real_crawler.py
    mock_python_script = tmp_path / "mock_crawler.py"
    mock_python_script.write_text("import time\ntime.sleep(2)\nprint('Mock Crawler Executed')\n", encoding="utf-8")
    
    # 建立論文中指定的 VBScript
    vbs_path = tmp_path / "Launch_Crawler_UI.vbs"
    vbs_code = f'''\' Launch_Crawler_UI.vbs
Set WshShell = CreateObject("WScript.Shell")
' 參數 1 代表 SW_SHOWNORMAL (強制顯示視窗)，False 代表不阻塞父進程
WshShell.Run "python ""{mock_python_script}""", 1, False
'''
    vbs_path.write_text(vbs_code, encoding="utf-8")
    
    # 測量執行時間，確認是否達成非阻塞 (Non-blocking)
    start_time = time.perf_counter()
    
    # 執行 VBScript
    result = subprocess.run(["cscript.exe", "//Nologo", str(vbs_path)], capture_output=True, text=True)
    
    end_time = time.perf_counter()
    duration = end_time - start_time
    
    # KPI 斷言 1: 父進程不被阻塞 (因為 mock script 跑 2 秒，如果非阻塞，這裡應該遠小於 1 秒)
    assert duration < 1.0, f"機制一失敗：VBScript 阻塞了父進程，耗時 {duration}s"
    
    # KPI 斷言 2: 執行成功，無系統錯誤
    assert result.returncode == 0
    assert "0x800700E8" not in result.stderr
