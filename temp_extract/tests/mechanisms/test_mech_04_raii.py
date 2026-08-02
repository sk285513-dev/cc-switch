import pytest
from playwright.async_api import async_playwright
import os
import asyncio
from pathlib import Path

@pytest.mark.asyncio
async def test_mechanism_04_raii_dead_code_elimination(tmp_path: Path):
    """
    機制四：絕對畫面捕捉與死碼消除之設計 (Resource Acquisition Is Initialization, RAII)
    測試在引發例外的情況下，finally 區塊的快照邏輯依然 100% 執行。
    """
    SCREENSHOT_DIR = tmp_path / "screenshots"
    SCREENSHOT_DIR.mkdir()
    
    total_states = 0
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 簡單 HTML
        await page.set_content("<html><body><h1>Test</h1></body></html>")
        
        # 故意製造 3 次迭代，其中第 2 次拋出例外
        for i in range(1, 4):
            try:
                if i == 2:
                    # 模擬 PlaywrightTimeoutError 或其他錯誤
                    await page.locator("non_existent_element").click(timeout=100)
            except Exception as e:
                print(f"   ⚠️ 操作發生異常: {e}")
            finally:
                # 無論成功或異常，保證執行狀態捕捉
                total_states += 1
                file_path = SCREENSHOT_DIR / f"State_{total_states:03d}.png"
                await page.screenshot(path=str(file_path))
                
        await browser.close()
        
    # KPI 斷言 1: total_states 應該精準推進到 3，即使中間拋出錯誤
    assert total_states == 3, "機制四失敗：計數器未能正確推進"
    
    # KPI 斷言 2: 實體檔案連續存在
    assert (SCREENSHOT_DIR / "State_001.png").exists(), "State_001.png 遺失"
    assert (SCREENSHOT_DIR / "State_002.png").exists(), "State_002.png 遺失 (死碼未消除)"
    assert (SCREENSHOT_DIR / "State_003.png").exists(), "State_003.png 遺失"
