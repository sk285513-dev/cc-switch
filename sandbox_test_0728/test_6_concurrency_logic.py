import sys
import os
import unittest
from pathlib import Path
from unittest.mock import patch

# 注入腳本路徑
script_dir = Path(r"C:\LocalAI_Workstation\scripts")
if str(script_dir) not in sys.path:
    sys.path.append(str(script_dir))

class TestConcurrencySafety(unittest.TestCase):
    
    def test_01_elastic_manager_floor_limit(self):
        """測試本地 20 並發降級機制，必須鎖死在 12 不可跌破"""
        from run_workflow import ElasticConcurrencyManager
        
        manager = ElasticConcurrencyManager(initial=20, min_val=12)
        self.assertEqual(manager.current, 20, "初始並發未能正確設定為 20")
        
        # 模擬遇到連續 15 次 OOM 崩潰
        for i in range(15):
            manager.step_down("fake_task", "Fake OOM Error")
            
        # 即使崩潰 15 次，底線必須守住 12
        self.assertEqual(manager.current, 12, "嚴重錯誤：彈性降級跌破了 12 的安全底線！")

    def test_02_cloud_stt_concurrency_unlocked(self):
        """測試雲端並發是否正確解封為 6，且徹底拔除 2 的限制"""
        with open(r"C:\LocalAI_Workstation\scripts\stt_runner.py", "r", encoding="utf-8") as f:
            code = f.read()
            
        self.assertNotIn('CHUNK_CONCURRENCY = 2', code, "嚴重錯誤：雲端並發仍被寫死為 2！")
        self.assertIn('get("stt_concurrency", 6)', code, "未正確實作動態讀取預設值 6")

if __name__ == "__main__":
    unittest.main()
