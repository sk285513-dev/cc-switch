import asyncio
import os
import re
from playwright.async_api import async_playwright

async def run():
    report_lines = ["# 自動化 UI 系統健檢報告 (Smart UI Crawler Report)\n"]
    has_errors = False
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()
        
        print("Navigating to http://localhost:8507...")
        await page.goto("http://localhost:8507", wait_until="networkidle")
        await page.wait_for_timeout(3000)
        
        # 尋找所有分頁 (tabs)
        tabs = page.locator("button[data-baseweb='tab']")
        count = await tabs.count()
        report_lines.append(f"**總計發現分頁數量：** {count} 個\n")
        print(f"Found {count} tabs to test.")
        
        for i in range(count):
            tab = tabs.nth(i)
            # 嘗試取得標題名稱，若無則用 Index
            tab_name = await tab.inner_text()
            tab_name = tab_name.strip()
            if not tab_name:
                tab_name = f"Tab_Index_{i}"
            
            # 清理檔名不允許的字元
            safe_name = re.sub(r'[\\/*?:"<>|]', "", tab_name).replace("\n", "_").replace(" ", "_")
            
            print(f"[{i+1}/{count}] Testing tab: {tab_name}...")
            report_lines.append(f"### 分頁 {i+1}: {tab_name}")
            
            try:
                # 點擊分頁
                await tab.click()
                await page.wait_for_timeout(2000) # 等待渲染
                
                # 截圖存證
                screenshot_path = f"C:/LocalAI_Workstation/test_results/tab_{i}_{safe_name}.png"
                await page.screenshot(path=screenshot_path)
                
                # 抓取頁面所有文字，檢查是否含有 Streamlit 崩潰關鍵字
                page_text = await page.inner_text("body")
                
                error_keywords = ["Traceback:", "NameError:", "ValueError:", "TypeError:", "ImportError:"]
                detected_errors = [kw for kw in error_keywords if kw in page_text]
                
                if detected_errors:
                    has_errors = True
                    print(f"  ❌ Error detected: {detected_errors}")
                    report_lines.append(f"- **狀態**：❌ 偵測到報錯 {detected_errors}")
                    report_lines.append(f"- **截圖存證**：![{tab_name}]({screenshot_path})")
                else:
                    print(f"  ✅ Passed")
                    report_lines.append(f"- **狀態**：✅ 正常加載，無報錯")
                    # 為了不讓報告太長，正常的也附上截圖供人類複查
                    report_lines.append(f"- **截圖存證**：![{tab_name}]({screenshot_path})")
                
            except Exception as e:
                has_errors = True
                print(f"  ❌ Playwright Exception: {e}")
                report_lines.append(f"- **狀態**：❌ 無法點擊或加載 ({str(e)})")
                
            report_lines.append("\n---\n")

        await browser.close()
    
    if not has_errors:
        report_lines.insert(1, "## 🏆 總結：所有分頁皆通過測試，無崩潰現象！\n")
    else:
        report_lines.insert(1, "## ⚠️ 總結：發現部分分頁存在異常報錯，請檢視以下細節。\n")
        
    with open("C:/LocalAI_Workstation/test_results/test_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print("Test complete. Report saved to test_results/test_report.md")

if __name__ == "__main__":
    asyncio.run(run())
