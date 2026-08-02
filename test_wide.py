import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Set a large viewport so all tabs are visible without sliding
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        await page.goto('http://localhost:8507/')
        await page.wait_for_timeout(5000)
        
        tabs = await page.locator('[role="tab"]').all()
        for tab in tabs:
            text = await tab.inner_text()
            print(f"Found tab: {text}")
            if '系統' in text or '時效' in text:
                print("Clicking target tab...")
                await tab.click()
                break
                
        await page.wait_for_timeout(3000)
        await page.screenshot(path='screenshot_wide.png')
        
        final_text = await page.locator('body').inner_text()
        if '管理 Gemini 免費金鑰池' in final_text:
            print('SUCCESS: Settings page found in DOM!')
        else:
            print('FAILURE: Settings page STILL not found in DOM.')
            
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
