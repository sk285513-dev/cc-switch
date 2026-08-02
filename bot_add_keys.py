import asyncio
from playwright.async_api import async_playwright
import os

RAW_KEYS_FILE = r"C:\Users\temp\.gemini\antigravity\brain\a7b0aaa8-bbf8-440f-95ac-6425b5de90ea\scratch\raw_keys.txt"
SCREENSHOT_PATH = r"C:\LocalAI_Workstation\keys_screenshot.png"

async def add_keys():
    print("🚀 [啟動] 注入 Gemini 金鑰池")
    
    with open(RAW_KEYS_FILE, "r", encoding="utf-8") as f:
        keys_data = f.read()
        
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()
        
        try:
            print("⏳ 正在連線至 Streamlit 伺服器...")
            await page.goto("http://localhost:8501", timeout=60000)
            await page.wait_for_selector(".stApp", timeout=30000)
            await asyncio.sleep(2)
            await page.wait_for_selector('button[data-baseweb="tab"]', timeout=30000)
            
            tabs = await page.locator('button[data-baseweb="tab"]').all()
            print("➡️ 進入分頁: 系統設定與開發者 (第7個)")
            await tabs[6].click(force=True)
            await asyncio.sleep(2)
            
            print("➡️ 尋找文字輸入框...")
            text_areas = await page.locator('textarea').all()
            if text_areas:
                print(f"找到 {len(text_areas)} 個 text_area...")
                for idx, ta in enumerate(text_areas):
                    try:
                        print(f"嘗試填寫第 {idx} 個...")
                        await ta.evaluate('(element, value) => { element.value = value; element.dispatchEvent(new Event("input", {bubbles: true})); element.dispatchEvent(new Event("change", {bubbles: true})); }', arg=keys_data)
                    except Exception as ex:
                        print(f"填寫第 {idx} 個失敗: {ex}")
            await asyncio.sleep(1)
            
            print("➡️ 點擊 解析原始數據...")
            buttons = await page.locator('button').all()
            for btn in buttons:
                text = await btn.inner_text()
                if "1." in text or "解析" in text or "1" in text:
                    if "執行專科智慧解析" in text:
                        continue
                    try:
                        print(f"點擊按鈕: {text}")
                        await btn.click(force=True)
                        break
                    except Exception:
                        pass
            
            print("⏳ 等待 5 秒讓系統處理並顯示成功訊息...")
            await asyncio.sleep(5)
            
            print(f"📸 截圖保存至 {SCREENSHOT_PATH}")
            await page.screenshot(path=SCREENSHOT_PATH, full_page=True)
            
        except Exception as e:
            print(f"💥 發生錯誤: {e}")
        finally:
            await browser.close()
            
if __name__ == "__main__":
    asyncio.run(add_keys())
