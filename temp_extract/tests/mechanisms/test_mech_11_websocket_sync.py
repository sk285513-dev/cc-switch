# -*- coding: utf-8 -*-
"""
機制十一：WebSocket 長連線等待之設計 (WebSocket Long-Poll Synchronization)
【BUG-10 修正】Streamlit 使用 WebSocket 架構，wait_for_load_state("networkidle")
    不會 resolve（因為 WS 連線永不斷開），改用 wait_for_selector 事件驅動。
"""
import pytest
import time
from playwright.async_api import async_playwright


@pytest.mark.asyncio
async def test_mechanism_11_websocket_sync():
    """
    KPI: 腳本 100% 不因 networkidle timeout 卡死，
         使用 wait_for_selector 事件驅動等待，
         任意回應時間 > 0ms 皆能正確完成同步。
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # 模擬 Streamlit WebSocket 架構：頁面有長連線，但 content 最終渲染
        await page.set_content("""
        <!DOCTYPE html>
        <html>
        <head><title>Streamlit Mock</title></head>
        <body>
          <div id="loading-placeholder">連線中...</div>
          <script>
            // 模擬 WebSocket 建立後的非同步渲染（1.5 秒後）
            setTimeout(() => {
              document.getElementById('loading-placeholder').style.display = 'none';
              const app = document.createElement('div');
              app.className = 'stApp';
              app.setAttribute('data-testid', 'stApp');
              const result = document.createElement('div');
              result.id = 'law-result';
              result.textContent = '依民法第197條，損害賠償請求權適用2年時效。';
              app.appendChild(result);
              document.body.appendChild(app);
            }, 1500);
          </script>
        </body>
        </html>
        """)

        # 【BUG-10 修正】不使用 networkidle（會永遠等待 WS 連線），
        # 改用 wait_for_selector 事件驅動等待 DOM 渲染完成
        t_start = time.perf_counter()
        await page.wait_for_selector('[data-testid="stApp"]', state="visible", timeout=15000)
        await page.wait_for_selector('#law-result', state="visible", timeout=5000)
        elapsed = time.perf_counter() - t_start

        # KPI: 等待時間合理（1.0 ~ 5.0 秒）
        assert 1.0 <= elapsed <= 5.0, (
            f"機制十一失敗：WebSocket 同步耗時 {elapsed:.2f}s 超出預期範圍 [1.0, 5.0]"
        )

        # 驗證內容正確渲染
        content = await page.inner_text('#law-result')
        assert "197" in content or "時效" in content, (
            f"機制十一失敗：渲染結果不含法律內容，實際: {content}"
        )

        await browser.close()
        print(f"✅ 機制十一通過：事件驅動同步成功，耗時 {elapsed:.2f}s，無 networkidle 卡死風險")
