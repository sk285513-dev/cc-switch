# ==============================================================================
# [CRITICAL DEPENDENCY WARNING] Group 9: 視覺化自我糾錯與 UI 自動測試 (Vision UI Testers)
# ------------------------------------------------------------------------------
# ⚠️ 此檔案屬於高度解耦架構的【Group 9】。
# 負責自動截圖與 OCR 解讀儀表板。一旦 Group 5 的畫面佈局改變，這裡的座標與關鍵字必須同步更新。
# 修改前請務必參閱：PIPELINE_DEPENDENCIES.md
# ==============================================================================
﻿import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('http://localhost:8507/')
        await page.wait_for_timeout(5000)
        
        # Take a screenshot before clicking
        await page.screenshot(path='screenshot_before.png')
        
        tabs = await page.locator('[role="tab"]').all()
        for tab in tabs:
            text = await tab.inner_text()
            if '系統' in text or '時效' in text:
                await tab.click()
                break
                
        await page.wait_for_timeout(3000)
        
        # Take a screenshot after clicking
        await page.screenshot(path='screenshot_after.png')
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
