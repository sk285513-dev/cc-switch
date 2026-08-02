# -*- coding: utf-8 -*-
"""
機制十二：動態 Tab 路由之設計 (Dynamic Tab Routing)
【BUG-02 修正】tabs[0].click() 固定點擊第一個 Tab，
    改為動態路由 tabs[idx % len(tabs)]，確保多 Tab 輪詢不越界。
"""
import pytest
from playwright.async_api import async_playwright


@pytest.mark.asyncio
async def test_mechanism_12_dynamic_tab_routing():
    """
    KPI-1: 100% Tab 命中率 — 每個 Tab 至少被訪問一次
    KPI-2: 零 IndexError — 動態 idx 路由不越界
    KPI-3: 狀態隔離驗證 — 每個 Tab 的 DOM content 不同
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Mock 多個法律 Tab
        await page.set_content("""
        <html><body>
          <button data-baseweb="tab" id="tab-0" role="tab">憲法</button>
          <button data-baseweb="tab" id="tab-1" role="tab">民法</button>
          <button data-baseweb="tab" id="tab-2" role="tab">刑法</button>
          <button data-baseweb="tab" id="tab-3" role="tab">行政法</button>
          <div id="content-area">請點擊 Tab</div>
          <script>
            document.querySelectorAll('[data-baseweb="tab"]').forEach((tab, i) => {
              tab.addEventListener('click', () => {
                document.getElementById('content-area').textContent = tab.textContent + ' 章節內容';
              });
            });
          </script>
        </body></html>
        """)

        tabs = await page.locator('[data-baseweb="tab"]').all()
        n_tabs = len(tabs)
        assert n_tabs == 4, f"機制十二失敗：預期 4 個 Tab，實際 {n_tabs} 個"

        # 模擬測試案例需要訪問 6 次 Tab（超過 Tab 數量）
        test_rounds = 6
        visited_tabs = []
        content_snapshots = []

        for idx in range(test_rounds):
            # 【BUG-02 修正】動態路由：tabs[idx % len(tabs)] 確保不越界
            target_idx = idx % n_tabs
            await tabs[target_idx].click()
            await page.wait_for_timeout(100)  # 給 JS 一點時間更新

            visited_tabs.append(target_idx)
            content = await page.inner_text('#content-area')
            content_snapshots.append(content)

        # KPI-1: 每個 Tab 至少被訪問一次
        for i in range(n_tabs):
            assert i in visited_tabs, f"機制十二失敗：Tab {i} 從未被訪問"
        print(f"  ✅ KPI-1: 所有 {n_tabs} 個 Tab 均被訪問，輪訪序列 = {visited_tabs}")

        # KPI-2: idx 路由不越界（如果越界 Playwright 會拋出 ElementHandleError）
        print(f"  ✅ KPI-2: {test_rounds} 次 Tab 路由無 IndexError")

        # KPI-3: 狀態隔離 — 前 n_tabs 次 content 應各自不同
        unique_contents = set(content_snapshots[:n_tabs])
        assert len(unique_contents) == n_tabs, (
            f"機制十二失敗：Tab 狀態隔離不足，唯一內容 {len(unique_contents)} 個（應 {n_tabs} 個）"
        )
        print(f"  ✅ KPI-3: {n_tabs} 個 Tab 狀態完全隔離")

        await browser.close()
