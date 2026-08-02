import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Navigating to http://localhost:8507...")
        await page.goto("http://localhost:8507")
        
        print("Waiting for page load...")
        await page.wait_for_timeout(5000)
        
        print("Clicking '系統與時效工具' tab...")
        # Find the tab by its exact text or partial text
        tab = page.locator("button[data-baseweb='tab']", has_text="系統與時效工具")
        
        count = await tab.count()
        if count > 0:
            print(f"Found {count} matching tab(s). Clicking...")
            await tab.first.click()
            await page.wait_for_timeout(5000)
            await page.screenshot(path="C:/LocalAI_Workstation/ui_step4_admin_tab.png")
            print("Saved ui_step4_admin_tab.png")
            
            # Now let's try to find the clean button
            clean_btn = page.locator("button", has_text="一鍵清理 401/403 死金鑰")
            if await clean_btn.count() > 0:
                print("Found clean button! The admin page rendered successfully.")
            else:
                print("Could not find the clean button. Admin page might not have rendered.")
        else:
            print("Could not find the '系統與時效工具' tab.")
            
        await browser.close()
        print("Test complete.")

asyncio.run(run())
