import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("http://localhost:8507")
        await page.wait_for_timeout(5000)
        
        print("Clicking text '⚙️ 系統與時效工具'...")
        try:
            await page.click('text="⚙️ 系統與時效工具"')
            await page.wait_for_timeout(3000)
            await page.screenshot(path="C:/LocalAI_Workstation/ui_step4_admin_tab.png")
            print("Successfully clicked and screenshotted admin tab.")
        except Exception as e:
            print(f"Error clicking: {e}")
            await page.screenshot(path="C:/LocalAI_Workstation/ui_step4_admin_error.png")
            
        await browser.close()

asyncio.run(run())
