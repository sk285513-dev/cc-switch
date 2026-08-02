import pytest
from playwright.async_api import async_playwright
import asyncio

@pytest.mark.asyncio
async def test_mechanism_05_semantic_dom_traversal():
    """
    機制五：空間感知遍歷之設計 (Semantic DOM Traversal)
    測試腳本是否能掃描全域 Tab，並成功透過迴圈進行空間轉移 (避免 StaleElement)。
    """
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head><title>SPA Tabs</title></head>
    <body>
        <div id="nav">
            <button data-baseweb="tab" id="tab1" onclick="switchTab(1)">Tab 1</button>
            <button data-baseweb="tab" id="tab2" onclick="switchTab(2)">Tab 2</button>
            <button data-baseweb="tab" id="tab3" onclick="switchTab(3)">Tab 3</button>
        </div>
        <div id="content">Content 1</div>
        <script>
            function switchTab(num) {
                // 模擬網路延遲與 DOM 替換
                setTimeout(() => {
                    document.getElementById('content').textContent = 'Content ' + num;
                }, 100);
            }
        </script>
    </body>
    </html>
    """
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(html_content)
        
        # 依照論文機制五實作:
        # Step 1: 抓取全域空間陣列
        tabs = await page.locator('button[data-baseweb="tab"]').all()
        
        # KPI 斷言 1: 必須抓到大於 0 個的 Tab
        assert len(tabs) == 3, "機制五失敗：無法正確建立狀態空間陣列"
        
        visited = 0
        
        # Step 2: 進行空間跳轉迴圈
        for idx in range(len(tabs)):
            try:
                # 重新定位以避免 StaleElementReferenceError (因為在 SPA 中按鈕可能被重繪)
                # 論文中直接 await tabs[idx].click()，若 Playwright auto-wait 正常發揮即不會報錯
                current_tab = page.locator('button[data-baseweb="tab"]').nth(idx)
                await current_tab.click()
                
                # 等待網路靜止 (以模擬)
                await page.wait_for_timeout(150) 
                visited += 1
                
                content = await page.inner_text("#content")
                assert content == f"Content {idx + 1}"
            except Exception as e:
                pytest.fail(f"機制五失敗：空間跳轉時發生異常 {e}")
                
        # KPI 斷言 2: 100% 分頁造訪率
        assert visited == 3, "機制五失敗：未能 100% 走訪所有 Tab"
        
        await browser.close()
