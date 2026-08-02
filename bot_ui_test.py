import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Navigating to http://localhost:8507...")
        await page.goto("http://localhost:8507")
        
        print("Waiting for page load...")
        await page.wait_for_timeout(10000)
        await page.screenshot(path="C:/LocalAI_Workstation/ui_step1_initial.png")
        print("Saved ui_step1_initial.png")
        
        # Click a tab or button - Let's try to find the tabs
        print("Looking for tabs...")
        tabs = await page.query_selector_all("button[data-baseweb='tab']")
        if tabs:
            print(f"Found {len(tabs)} tabs. Clicking the second tab...")
            if len(tabs) > 1:
                await tabs[1].click()
                await page.wait_for_timeout(5000)
                await page.screenshot(path="C:/LocalAI_Workstation/ui_step2_tab2.png")
                print("Saved ui_step2_tab2.png")
                
                print("Clicking the third tab...")
                if len(tabs) > 2:
                    await tabs[2].click()
                    await page.wait_for_timeout(5000)
                    await page.screenshot(path="C:/LocalAI_Workstation/ui_step3_tab3.png")
                    print("Saved ui_step3_tab3.png")
        else:
            print("No tabs found.")
            
        await browser.close()
        print("Test complete.")

asyncio.run(run())
