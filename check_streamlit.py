import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print('Navigating...')
        await page.goto('http://localhost:8501', timeout=60000)
        print('Waiting for .stApp...')
        await page.wait_for_selector('.stApp', timeout=120000)
        print('Waiting for tabs...')
        await page.wait_for_selector('button[data-baseweb="tab"]', timeout=180000)
        print('Tabs loaded successfully!')
        await browser.close()
asyncio.run(run())
