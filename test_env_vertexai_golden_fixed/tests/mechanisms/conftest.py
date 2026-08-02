"""
tests/mechanisms/conftest.py
【SA-01 修正】將 check_for_crash 提升至 conftest.py 共享層，
避免在各機制測試中重複定義，確保單一事實來源 (Single Source of Truth)。
"""
import pytest
from playwright.async_api import Page


async def check_for_crash(page: Page) -> bool:
    """
    隱式動態神諭 (Implicit Dynamic Oracle)。
    在每次狀態快照前掃描 document.body 純文本，
    比對崩潰特徵碼，時間複雜度 O(K×M)。
    """
    page_text = await page.inner_text("body")
    error_keywords = ["Traceback", "Exception:", "st.error", "IndexError"]
    for kw in error_keywords:
        if kw in page_text:
            print(f"   🚨 偵測到系統崩潰紅字: {kw}")
            return True
    return False
