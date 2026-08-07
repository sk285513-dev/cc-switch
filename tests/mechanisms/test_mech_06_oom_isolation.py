import pytest
from playwright.async_api import async_playwright
import os
import asyncio
import psutil
from pathlib import Path

@pytest.mark.asyncio
async def test_mechanism_06_oom_isolation(tmp_path: Path):
    """
    機制六：全面實體留存與 OOM 迴避之設計 (Disk I/O Isolation)
    測試腳本將連續拍攝截圖並直接存檔，驗證 Python 記憶體不會線性增長。
    """
    SCREENSHOT_DIR = tmp_path / "screenshots"
    SCREENSHOT_DIR.mkdir()
    
    process = psutil.Process(os.getpid())
    
    # 紀錄初始記憶體 ( bytes 轉 MB )
    ram_start = process.memory_info().rss / (1024 * 1024)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content("<html><body><h1>Memory Leak Test</h1></body></html>")
        
        # 模擬高頻率截圖 100 次
        for i in range(1, 101):
            file_path = SCREENSHOT_DIR / f"State_{i:03d}.png"
            # 絕對路徑直接落地，繞過 Python Heap
            await page.screenshot(path=str(file_path))
            
        await browser.close()
        
    # 紀錄結束記憶體
    ram_end = process.memory_info().rss / (1024 * 1024)
    ram_diff = ram_end - ram_start
    
    print(f"\\n初始記憶體: {ram_start:.2f} MB")
    print(f"結束記憶體: {ram_end:.2f} MB")
    print(f"記憶體增長: {ram_diff:.2f} MB")
    
    # KPI 斷言 1: 記憶體絕對平滑 (Memory Flatten / No OOM)
    # 嚴格要求 100 張截圖的過程中，記憶體增長不得超過 15 MB
    assert ram_diff < 15.0, f"機制六失敗：發生 Memory Leak，記憶體異常增長 {ram_diff:.2f} MB"
    
    # KPI 斷言 2: 實體檔案 100% 落地 (Direct Disk I/O)
    file_count = len(list(SCREENSHOT_DIR.iterdir()))
    assert file_count == 100, f"機制六失敗：檔案遺失，預期 100 張，實際 {file_count} 張"
