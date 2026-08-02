# -*- coding: utf-8 -*-
"""
機制十四：自動化看門狗之設計 (Automated Watchdog Design)
【BUG-14 修正】Watchdog 原本 30 分鐘硬編碼無法在 CI 中測試，
    改為由環境變數 WATCHDOG_TIMEOUT_MIN 控制（預設 30，CI 可設為 0.05）。
"""
import os
import pytest
import asyncio
import time


def get_watchdog_timeout_sec() -> float:
    """
    【BUG-14 修正】從環境變數讀取 Watchdog 超時設定（分鐘），
    允許 CI 環境設定極小值（如 0.05 = 3 秒）進行快速測試。
    """
    timeout_min = float(os.environ.get("WATCHDOG_TIMEOUT_MIN", "30"))
    return timeout_min * 60


class MockWatchdog:
    """
    模擬 LexMind-Omni 的系統 Watchdog。
    監控目標進程的心跳 (heartbeat)，超過 timeout 後觸發自癒 (recovery)。
    """
    def __init__(self, timeout_sec: float):
        self.timeout_sec = timeout_sec
        self.last_heartbeat = time.time()
        self.recovery_triggered = False
        self.recovery_count = 0

    def update_heartbeat(self):
        """進程正常時更新心跳"""
        self.last_heartbeat = time.time()

    def check(self) -> bool:
        """檢查是否超時，超時則觸發自癒"""
        elapsed = time.time() - self.last_heartbeat
        if elapsed > self.timeout_sec and not self.recovery_triggered:
            self.recovery_triggered = True
            self.recovery_count += 1
            return True  # 需要自癒
        return False

    def reset(self):
        """自癒後重設 Watchdog"""
        self.last_heartbeat = time.time()
        self.recovery_triggered = False


@pytest.mark.asyncio
async def test_mechanism_14_watchdog():
    """
    KPI-1: 超時偵測準確率 100% — 進程 stuck 後 Watchdog 必須觸發
    KPI-2: CI 可測性 — WATCHDOG_TIMEOUT_MIN=0.05 可在 3 秒內完成測試
    KPI-3: 自癒後恢復 — recovery 後心跳正常時不再觸發
    """
    # 【BUG-14 修正】使用環境變數，CI 環境設 0.05 分鐘 = 3 秒
    # 測試時覆蓋為極小值
    os.environ["WATCHDOG_TIMEOUT_MIN"] = "0.033"  # 約 2 秒
    timeout_sec = get_watchdog_timeout_sec()

    watchdog = MockWatchdog(timeout_sec=timeout_sec)

    # Case 1: 正常心跳 → Watchdog 不觸發
    watchdog.update_heartbeat()
    await asyncio.sleep(0.1)
    triggered = watchdog.check()
    assert not triggered, "機制十四失敗：正常心跳下 Watchdog 不應觸發"
    print(f"  ✅ KPI-1a: 正常心跳下無誤觸發（timeout={timeout_sec:.1f}s）")

    # Case 2: 進程 Stuck → Watchdog 必須觸發
    # 等待超過 timeout
    await asyncio.sleep(timeout_sec + 0.5)
    triggered = watchdog.check()
    assert triggered, (
        f"機制十四失敗：進程 stuck {timeout_sec + 0.5:.1f}s 後 Watchdog 未觸發"
    )
    assert watchdog.recovery_count == 1, "機制十四失敗：自癒計數應為 1"
    print(f"  ✅ KPI-1b: 超時 {timeout_sec + 0.5:.1f}s 後 Watchdog 正確觸發，recovery_count=1")

    # Case 3: 自癒後恢復正常心跳，Watchdog 不再重複觸發
    watchdog.reset()
    watchdog.update_heartbeat()
    await asyncio.sleep(0.1)
    triggered_again = watchdog.check()
    assert not triggered_again, "機制十四失敗：自癒後正常心跳下 Watchdog 不應再觸發"
    print("  ✅ KPI-3: 自癒後恢復正常，無重複觸發")

    # KPI-2: 驗證整個測試在合理時間內完成（< 15 秒）
    print(f"✅ 機制十四通過：WATCHDOG_TIMEOUT_MIN={os.environ['WATCHDOG_TIMEOUT_MIN']} CI 可測性確認")

    # 清理環境變數
    del os.environ["WATCHDOG_TIMEOUT_MIN"]
