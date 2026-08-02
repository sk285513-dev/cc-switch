import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('http://localhost:8501')
        await asyncio.sleep(5)
        html = await page.content()
        with open('C:/LocalAI_Workstation/dom_dump.txt', 'w', encoding='utf-8') as f:
            f.write(html)
        await browser.close()
asyncio.run(run())
