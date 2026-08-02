import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("http://localhost:8507")
        await page.wait_for_timeout(5000)
        await page.screenshot(path="C:/LocalAI_Workstation/test_manual.png")
        await browser.close()
asyncio.run(run())
