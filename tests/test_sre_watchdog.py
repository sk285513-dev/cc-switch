import sys
import os
import unittest
from datetime import datetime, timedelta

# Add scripts directory to path to import sre_watchdog
sys.path.append(os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'scripts')))

from sre_watchdog import SREWatchdog
import sre_watchdog

class TestSREWatchdogLogic(unittest.TestCase):
    def setUp(self):
        # Mock show_toast to catch alerts without spawning GUI or sending emails
        self.alerts_triggered = []
        self.original_show_toast = sre_watchdog.show_toast
        sre_watchdog.show_toast = lambda title, msg, is_error=True: self.alerts_triggered.append((title, msg))
        
        self.wd = SREWatchdog()

    def tearDown(self):
        # Restore original function
        sre_watchdog.show_toast = self.original_show_toast

    def test_fallback_error_detection(self):
        """Test if the watchdog catches 'fallback to direct merge' which is an implicit error."""
        log_line = "2026-07-26 10:00:00 [WARNING] fallback to direct merge because vertex failed"
        
        # Simulate triggering the threshold (ERROR_COUNT_THRESHOLD is 3)
        for _ in range(3):
            self.wd.parse_and_alert(log_line, "dummy_workflow.log")
            
        # Check if an alert containing the storm warning was fired
        alert_fired = any("系統異常風暴警報" in title for title, msg in self.alerts_triggered)
        self.assertTrue(alert_fired, "SRE Watchdog failed to detect the implicit fallback error!")

    def test_strict_progress_heartbeat(self):
        """Test if the watchdog strictly requires QualityGate to reset the heartbeat."""
        # 1. A garbage log should NOT reset the heartbeat
        old_progress_time = datetime.now() - timedelta(minutes=10)
        self.wd.last_progress_activity = old_progress_time
        
        self.wd.parse_and_alert("2026-07-26 10:05:00 [INFO] 任務成功完成", "dummy.log")
        self.assertEqual(self.wd.last_progress_activity, old_progress_time, "Watchdog was fooled by a fake '完成' log!")
        
        # 2. A true QualityGate log SHOULD reset the heartbeat
        self.wd.parse_and_alert("2026-07-26 10:06:00 [INFO] [QualityGate] PASSED.", "dummy.log")
        self.assertGreater(self.wd.last_progress_activity, old_progress_time, "Watchdog failed to reset heartbeat on QualityGate!")

if __name__ == '__main__':
    unittest.main()
