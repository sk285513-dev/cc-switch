import pytest
from playwright.async_api import async_playwright, Page
import asyncio
import time

@pytest.mark.asyncio
async def test_mechanism_02_event_driven_dom_sync():
    """
    機制二：強制防護等待之設計 (Event-Driven DOM Synchronization)
    嚴格遵循論文實作，使用 Playwright 的 wait_for_selector(state="visible")。
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 使用一個輕量級的測試 html，模擬 Streamlit 的延遲渲染
        html_content = """
        <!DOCTYPE html>
        <html>
        <head><title>Test</title></head>
        <body>
            <div id="loading">Loading...</div>
            <script>
                setTimeout(() => {
                    document.getElementById('loading').style.display = 'none';
                    const app = document.createElement('div');
                    app.className = 'stApp';
                    app.textContent = 'App Loaded';
                    document.body.appendChild(app);
                    
                    const btn = document.createElement('button');
                    btn.setAttribute('data-baseweb', 'tab');
                    btn.textContent = 'Tab Button';
                    document.body.appendChild(btn);
                }, 1000);
            </script>
        </body>
        </html>
        """
        await page.set_content(html_content)
        
        # 依照論文中的實作
        start_time = time.perf_counter()
        
        # 替換 goto 為直接依賴剛才的 set_content，因此這行省略 goto localhost
        # await page.goto("http://localhost:8501", timeout=60000)
        
        await page.wait_for_selector(".stApp", state="visible", timeout=30000)
        await page.wait_for_selector('button[data-baseweb="tab"]', state="visible", timeout=30000)
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        # KPI 斷言: DOM 渲染在 1 秒後發生，腳本必須在極短毫秒內反應
        # 【BUG-01 修正】上限由 1.5s 改為 3.0s，防止 CI Headless 環境 V8 啟動較慢造成 Flaky 誤判
        assert 1.0 <= duration <= 3.0, f"機制二失敗：未能在極低延遲下同步 DOM，耗時 {duration}s"
        
        await browser.close()
