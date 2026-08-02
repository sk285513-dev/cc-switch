import asyncio
import os
import re
from playwright.async_api import async_playwright

TEST_DIR = "C:/LocalAI_Workstation/test_results/ultimate_full"
os.makedirs(TEST_DIR, exist_ok=True)

async def check_errors_in_page(page, context_name, report_lines):
    page_text = await page.inner_text("body")
    error_keywords = ["Traceback:", "NameError:", "ValueError:", "TypeError:", "ImportError:", "Exception:"]
    detected_errors = [kw for kw in error_keywords if kw in page_text]
    
    screenshot_path = os.path.join(TEST_DIR, f"{context_name}.png")
    await page.screenshot(path=screenshot_path)
    
    if detected_errors:
        print(f"  ❌ [{context_name}] Error detected: {detected_errors}")
        report_lines.append(f"- **狀態**: ❌ 異常 ({detected_errors})")
        report_lines.append(f"- **截圖**: ![]({screenshot_path})\n")
        return False
    
    if len(page_text.strip()) < 20:
        print(f"  ⚠️ [{context_name}] Blank Screen")
        report_lines.append(f"- **狀態**: ⚠️ 破圖或白畫面")
        report_lines.append(f"- **截圖**: ![]({screenshot_path})\n")
        return False
        
    print(f"  ✅ [{context_name}] OK")
    return True

async def run_full_test():
    report_lines = ["# 🛡️ Ultimate UI Crawler - 全域放火壓力測試報告\n"]
    
    print("啟動全域深度爬蟲...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()
        
        print("導航至 http://localhost:8507...")
        await page.goto("http://localhost:8507", wait_until="networkidle")
        await page.wait_for_selector("button[data-baseweb='tab']", timeout=15000)
        await page.wait_for_timeout(3000)
        
        tabs = page.locator("button[data-baseweb='tab']")
        count = await tabs.count()
        # 限制在主要的 8 個分頁，避免 Playwright 在不可見的嵌套子分頁中超時
        main_tab_count = min(count, 8) 
        
        for i in range(main_tab_count):
            # 確保重新取得元素以防止 Stale Element Reference
            tabs = page.locator("button[data-baseweb='tab']")
            tab = tabs.nth(i)
            tab_name = await tab.inner_text()
            tab_name = tab_name.replace('\n', '').strip()
            print(f"\n--- Testing Tab {i+1}: {tab_name} ---")
            report_lines.append(f"## 測試分頁：{tab_name}")
            
            await tab.click()
            await page.wait_for_timeout(2000) # 等待頁面與 Spinner 載入
            
            # 狀態 1: Idle
            report_lines.append(f"### 狀態: 初始載入 (Idle)")
            await check_errors_in_page(page, f"Tab{i}_Idle", report_lines)
            
            # 狀態 2: 遍歷與展開所有 Expander
            expanders = page.locator("div[data-testid='stExpander'] summary")
            exp_count = await expanders.count()
            if exp_count > 0:
                print(f"發現 {exp_count} 個可展開面板...")
                for j in range(exp_count):
                    try:
                        expanders = page.locator("div[data-testid='stExpander'] summary")
                        exp = expanders.nth(j)
                        if await exp.is_visible():
                            exp_text = await exp.inner_text()
                            exp_text = exp_text.replace('\n', '').strip()[:20]
                            await exp.click()
                            await page.wait_for_timeout(1000)
                            report_lines.append(f"### 狀態: 展開面板 [{exp_text}]")
                            await check_errors_in_page(page, f"Tab{i}_Exp_{j}", report_lines)
                    except Exception as e:
                        print(f"Skipping expander {j}: {e}")

        await browser.close()
        
    with open("C:/LocalAI_Workstation/test_results/ultimate_full/ultimate_test_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print("全域放火測試完畢！報告已儲存。")

if __name__ == "__main__":
    asyncio.run(run_full_test())
