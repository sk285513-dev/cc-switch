import asyncio
from playwright.async_api import async_playwright
import os

async def run():
    print("啟動 Playwright 沙盒測試...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("連線至 Streamlit 伺服器 (http://localhost:8507)...")
        await page.goto("http://localhost:8507", wait_until="networkidle")
        
        print("等待分頁元件載入...")
        await page.wait_for_selector('button[data-baseweb="tab"]', timeout=60000)
        
        print("尋找「⚙️ 系統與時效工具」分頁...")
        tabs = await page.locator('button[data-baseweb="tab"]').all()
        
        clicked = False
        for tab in tabs:
            text = await tab.inner_text()
            if "系統與時效工具" in text or "⚙️" in text:
                await tab.click()
                print("成功點擊設定分頁！")
                clicked = True
                break
                
        if not clicked:
            print("找不到設定分頁，測試失敗！")
            await browser.close()
            return

        print("等待畫面重新渲染 (10秒)...")
        await page.wait_for_timeout(10000)
        
        screenshot_path = "C:\\LocalAI_Workstation\\verify_settings_after_fix2.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"畫面擷取成功，已儲存至：{screenshot_path}")
        
        # 檢查 DOM 內容
        content = await page.content()
        if "一鍵清理" in content:
            print("🎉 驗證成功：DOM 內包含「一鍵清理」！")
        else:
            print("⚠️ 警告：DOM 內仍無內容！")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
