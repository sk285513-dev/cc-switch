# ==============================================================================
# [CRITICAL DEPENDENCY WARNING] Group 9: 視覺化自我糾錯與 UI 自動測試 (Vision UI Testers)
# ------------------------------------------------------------------------------
# ⚠️ 此檔案屬於高度解耦架構的【Group 9】。
# 負責自動截圖與 OCR 解讀儀表板。一旦 Group 5 的畫面佈局改變，這裡的座標與關鍵字必須同步更新。
# 修改前請務必參閱：PIPELINE_DEPENDENCIES.md
# ==============================================================================
import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print('Navigating...')
        await page.goto('http://localhost:8501', timeout=60000)
        await asyncio.sleep(5) # wait for error to render
        await page.screenshot(path='error_screenshot.png')
        print('Screenshot saved to error_screenshot.png')
        
        # also try to get all text
        text = await page.evaluate("document.body.innerText")
        with open("error_text.txt", "w", encoding="utf-8") as f:
            f.write(text)
            
        await browser.close()
asyncio.run(run())
