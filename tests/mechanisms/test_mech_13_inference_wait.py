# -*- coding: utf-8 -*-
"""
機制十三：推論等待之設計 (AI Inference Wait Mechanism)
【BUG-07 修正】wait_for_inference 中的裸 except: pass 會吞掉關鍵錯誤，
    改為記錄具體錯誤類型並重拋非預期例外。
"""
import pytest
import time
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError


INFERENCE_TIMEOUT_MS = 30000  # 30 秒，CI 可設定為更小
SPINNER_SELECTOR = '[data-testid="stSpinner"]'
RESULT_SELECTOR = '[data-testid="stMarkdown"], .stApp p'


async def wait_for_inference(page, timeout_ms: int = INFERENCE_TIMEOUT_MS) -> float:
    """
    【BUG-07 修正】等待 AI 推論完成。
    原始裸 except: pass 會完全吞掉 TimeoutError，導致程序繼續執行讀取到空結果。
    修正後：
    - PlaywrightTimeoutError → 記錄並重拋，讓測試正確失敗
    - 其他 Exception → 記錄 Warning 但不靜默吞掉
    """
    t_start = time.perf_counter()
    try:
        # 等待 Spinner 消失（推論中）
        await page.wait_for_selector(SPINNER_SELECTOR, state="hidden", timeout=timeout_ms)
    except PlaywrightTimeoutError as e:
        # 【BUG-07 修正】明確重拋 PlaywrightTimeoutError，不靜默
        raise AssertionError(
            f"推論等待逾時 ({timeout_ms}ms)：AI Spinner 未消失，系統可能卡死。原始錯誤: {e}"
        )
    except Exception as e:
        # 【BUG-07 修正】非逾時的非預期錯誤也要記錄，不吞掉
        print(f"  ⚠️ wait_for_inference 遭遇非預期例外（已記錄）: {type(e).__name__}: {e}")
        raise

    elapsed = time.perf_counter() - t_start
    return elapsed


@pytest.mark.asyncio
async def test_mechanism_13_inference_wait():
    """
    KPI-1: Spinner 消失偵測率 100% — 推論完成後 Spinner 必須消失
    KPI-2: Timeout 正確重拋 — 逾時不靜默吞掉，確保測試失敗有明確訊息
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Case 1: 推論成功（Spinner 在 1s 後消失）
        await page.set_content("""
        <html><body>
          <div data-testid="stSpinner" id="spinner">推論中...</div>
          <script>
            setTimeout(() => {
              document.getElementById('spinner').style.display = 'none';
              const md = document.createElement('div');
              md.setAttribute('data-testid', 'stMarkdown');
              md.textContent = '依民法第197條，損害賠償請求權，自請求權人知有損害時起2年消滅。';
              document.body.appendChild(md);
            }, 1000);
          </script>
        </body></html>
        """)

        elapsed = await wait_for_inference(page, timeout_ms=5000)
        assert 0.5 <= elapsed <= 3.0, (
            f"機制十三失敗：推論等待耗時 {elapsed:.2f}s，超出正常範圍 [0.5, 3.0]"
        )
        print(f"  ✅ KPI-1: Spinner 消失成功，耗時 {elapsed:.2f}s")

        # Case 2: 驗證 Timeout 不靜默（使用不會消失的 Spinner）
        await page.set_content("""
        <html><body>
          <div data-testid="stSpinner">永久推論中（模擬卡死）...</div>
        </body></html>
        """)

        timeout_raised = False
        try:
            await wait_for_inference(page, timeout_ms=500)  # 極短 timeout 觸發
        except AssertionError as e:
            # 期望此路徑：timeout 被正確重拋為 AssertionError
            timeout_raised = True
            print(f"  ✅ KPI-2: Timeout 正確重拋，訊息: {str(e)[:80]}...")

        assert timeout_raised, "機制十三失敗：Timeout 被靜默吞掉，BUG-07 修正未生效"

        await browser.close()
        print("✅ 機制十三通過：推論等待逾時正確重拋，BUG-07 修正驗證成功")
