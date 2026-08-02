import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        await page.goto('http://localhost:8507/')
        await page.wait_for_timeout(5000)
        
        # Dump the innerText of the whole page
        text = await page.locator('body').inner_text()
        with open('dom_dump.txt', 'w', encoding='utf-8') as f:
            f.write(text)
            
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
