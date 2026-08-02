import asyncio
from playwright.async_api import async_playwright
import sys

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("Navigating to app...")
        await page.goto('http://localhost:8507/')
        await page.wait_for_timeout(5000)  # Wait for initial load
        
        # Streamlit 1.58.0 structure check
        print("Getting page text...")
        main_text = await page.locator('body').inner_text()
        
        # Click the tab "⚙️ 系統與時效工具"
        print("Looking for tab...")
        try:
            # wait for tabs to appear
            await page.wait_for_selector('[role="tab"]', timeout=10000)
            tabs = await page.locator('[role="tab"]').all()
            found = False
            for tab in tabs:
                text = await tab.inner_text()
                if '系統' in text or '時效' in text:
                    print(f"Clicking tab: {text}")
                    await tab.click()
                    found = True
                    break
            if not found:
                print("Could not find the target tab.")
        except Exception as e:
            print(f"Error finding/clicking tab: {e}")
            
        await page.wait_for_timeout(3000)  # Wait for tab to render
        
        print("Checking final DOM...")
        final_text = await page.locator('body').inner_text()
        print('--- APP TEXT ---')
        print(final_text[:1000])
        
        if '管理 Gemini 免費金鑰池' in final_text:
            print('SUCCESS: Settings page rendered!')
            sys.exit(0)
        else:
            print('FAILURE: Settings page not found in DOM.')
            sys.exit(1)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
