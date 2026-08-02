import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("http://localhost:8507")
        await page.wait_for_timeout(5000)
        
        tabs = await page.query_selector_all("button[data-baseweb='tab']")
        with open('C:/LocalAI_Workstation/tab_names.txt', 'w', encoding='utf-8') as f:
            for i, tab in enumerate(tabs):
                text = await tab.inner_text()
                f.write(f"Tab {i}: {text.strip()}\n")
            
        await browser.close()

asyncio.run(run())
