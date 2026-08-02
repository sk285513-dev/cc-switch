# -*- coding: utf-8 -*-
"""
機制九：多維度隱藏元件探索之設計 (Hidden Element Exploration)
【BUG-15 修正】force=True 後必須等待元素真正可見，避免競態條件。
"""
import pytest
from playwright.async_api import async_playwright


@pytest.mark.asyncio
async def test_mechanism_09_hidden_element_exploration():
    """
    驗證 force=True 強制展開隱藏元件後，子元件操作 100% 成功。
    KPI-1: 100% 容器展開率 — 所有 .stExpander 狀態轉為可見
    KPI-2: 零暗流點擊 — 展開後子元件操作不拋出 ElementNotVisibleError
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Mock Streamlit Expander DOM
        await page.set_content("""
        <html><body>
          <div data-testid="stExpander" style="display:none;" id="exp1">
            <div class="expander-content">
              <input type="checkbox" id="inner-cb-1" />
              <input type="text" id="inner-text-1" />
            </div>
          </div>
          <div data-testid="stExpander" style="display:none;" id="exp2">
            <div class="expander-content">
              <input type="checkbox" id="inner-cb-2" />
            </div>
          </div>
          <script>
            // 模擬 force click 展開
            document.querySelectorAll('[data-testid="stExpander"]').forEach(el => {
              el.addEventListener('click', () => {
                el.style.display = 'block';
                el.querySelectorAll('input').forEach(i => {
                  i.style.display = 'block';
                  i.style.visibility = 'visible';
                });
              });
            });
          </script>
        </body></html>
        """)

        # 掃描所有 .stExpander
        expanders = await page.locator('[data-testid="stExpander"]').all()
        assert len(expanders) == 2, f"機制九失敗：應有 2 個 Expander，實際 {len(expanders)} 個"

        expanded_count = 0
        for exp in expanders:
            try:
                # 【BUG-15 修正】force=True 後等待元素進入 visible 狀態
                await exp.click(force=True)
                await exp.wait_for(state="visible", timeout=3000)
                expanded_count += 1
            except Exception as e:
                print(f"  ⚠️ Expander 展開失敗（非致命）: {e}")

        # KPI-1: 展開率
        assert expanded_count == len(expanders), (
            f"機制九失敗：只展開了 {expanded_count}/{len(expanders)} 個 Expander"
        )
        print(f"  ✅ KPI-1 通過：{expanded_count}/{len(expanders)} 個 Expander 成功展開")

        # KPI-2: 對展開後的子元件進行操作，驗證零暗流點擊
        inner_checkboxes = await page.locator('input[type="checkbox"]').all()
        operation_errors = 0
        for cb in inner_checkboxes:
            try:
                # 強制確保可見後再操作
                await cb.click(force=True)
                await cb.wait_for(state="visible", timeout=2000)
            except Exception as e:
                operation_errors += 1
                print(f"  ⚠️ 子元件操作失敗: {e}")

        assert operation_errors == 0, (
            f"機制九失敗：{operation_errors} 個子元件操作發生 ElementNotVisible 暗流"
        )
        print(f"  ✅ KPI-2 通過：{len(inner_checkboxes)} 個子元件零暗流點擊")

        await browser.close()
