import pytest
from playwright.async_api import async_playwright, Page
# 【SA-01 修正】check_for_crash 已提升至 conftest.py 統一管理，此處 import 共享版本
from tests.mechanisms.conftest import check_for_crash


@pytest.mark.asyncio
async def test_mechanism_03_implicit_dynamic_oracles():
    """
    機制三：崩潰紅字防禦之設計 (Implicit Dynamic Oracles)
    測試 100% 阻斷紅字髒資料的能力。
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # 測試 1: 正常頁面，不該觸發
        page_normal = await browser.new_page()
        await page_normal.set_content("<html><body><h1>Hello World</h1><p>This is a normal page.</p></body></html>")
        has_crash = await check_for_crash(page_normal)
        assert not has_crash, "機制三失敗：正常頁面被誤判為崩潰"
        
        # 測試 2: 注入紅字 Traceback 的崩潰頁面
        page_crash = await browser.new_page()
        await page_crash.set_content("<html><body><h1>Error</h1><p>Traceback (most recent call last):</p></body></html>")
        has_crash2 = await check_for_crash(page_crash)
        assert has_crash2, "機制三失敗：未能攔截 Traceback 崩潰"
        
        # 測試 3: 注入 st.error 的崩潰頁面
        page_st_error = await browser.new_page()
        await page_st_error.set_content("<html><body><div>st.error: Invalid input</div></body></html>")
        has_crash3 = await check_for_crash(page_st_error)
        assert has_crash3, "機制三失敗：未能攔截 st.error 崩潰"
        
        await browser.close()
