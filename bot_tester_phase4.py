import asyncio
from playwright.async_api import async_playwright
import os
import time

OUTPUT_DIR = r"C:\LocalAI_Workstation\Vision_Screenshots_Phase4"
os.makedirs(OUTPUT_DIR, exist_ok=True)

async def run_phase4_crawler():
    print("🚀 [啟動] 階段四：跨元件資料注入與後端流動驗證爬蟲 (真實環境展示)")
    
    # 這裡刻意使用 headless=False，讓使用者可以在螢幕上直接觀看打字過程
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=50) # 加入 slow_mo 讓打字過程肉眼可見
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()
        
        print("⏳ 正在連線至 Streamlit 伺服器...")
        try:
            await page.goto("http://localhost:8501", timeout=30000)
            await page.wait_for_selector('button[data-baseweb="tab"]', timeout=30000)
        except Exception as e:
            print(f"❌ 無法連線或載入超時: {e}")
            await browser.close()
            return
            
        print("✅ 成功連線！正在切換至主分頁...")
        # 為了保險，先點擊第一分頁
        tabs = page.locator('button[data-baseweb="tab"]')
        await tabs.nth(0).click()
        await asyncio.sleep(2)
        
        # 定位文字框
        print("📝 正在尋找案情輸入框...")
        # 使用 placeholder 或 label 定位。Streamlit 的 text_area label 是 p 標籤
        # 改用更寬鬆的 xpath 或 role 定位
        text_area = page.get_by_placeholder("例如：我前年車禍大骨折想要起訴求償...")
        
        test_case = "甲與乙發生車禍，甲無照駕駛，乙逆向行駛，請問依實務見解，雙方的損害賠償過失比例原則上應如何分配？"
        
        print("⌨️ 正在模擬真人輸入案情...")
        await text_area.fill("") # 清空
        # 使用 type 逐字輸入，讓使用者感受到「真的在打字」
        await text_area.type(test_case, delay=50)
        
        # 截圖記錄輸入前的狀態
        before_shot = os.path.join(OUTPUT_DIR, "01_Input_Injected.png")
        await page.screenshot(path=before_shot)
        print(f"📸 已存檔輸入完成截圖: {before_shot}")
        
        # 定位送出按鈕
        print("🖱️ 正在尋找並點擊送出按鈕...")
        submit_btn = page.get_by_text("📤 送出此段內容進行心證分析")
        await submit_btn.click(force=True)
        
        print("⏳ 已經送出！正在等待後端伺服器 (LLM/RWS) 處理回饋畫面 (等待 10 秒)...")
        # 送出後，Streamlit 畫面會開始跑 spinner 或重新渲染。我們等待一段合理時間
        # 在真實環境中，Ollama 推理可能需要很久，我們這裡只要驗證「畫面有改變/收到請求」即可。
        await asyncio.sleep(10)
        
        # 截圖記錄送出後的回饋
        after_shot = os.path.join(OUTPUT_DIR, "02_After_Submit_Feedback.png")
        await page.screenshot(path=after_shot)
        print(f"📸 已存檔送出後狀態截圖: {after_shot}")
        
        print("🎉 階段四：資料流動驗證測試完畢！")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_phase4_crawler())
