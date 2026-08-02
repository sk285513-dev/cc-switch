import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        await page.goto('http://localhost:8507/')
        await page.wait_for_timeout(5000)
        
        # Click by exact text
        print("Clicking tab...")
        await page.get_by_text("⚙️ 系統與時效工具").click()
        
        await page.wait_for_timeout(3000)
        await page.screenshot(path='screenshot_final.png')
        
        text = await page.locator('body').inner_text()
        if '一鍵清理 401' in text or '企業級架構與金鑰池設定介面' in text:
            print("SUCCESS")
        else:
            print("FAILURE")
            
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
