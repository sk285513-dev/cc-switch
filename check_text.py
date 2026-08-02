import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('http://localhost:8507', wait_until='networkidle')
        await page.wait_for_timeout(3000)
        text = await page.inner_text('body')
        print('--- EXTRACTED TEXT FROM BODY ---')
        print(text)
        print('--- END TEXT ---')
        print(f'Length: {len(text.strip())}')
        await browser.close()

asyncio.run(run())
