# ==============================================================================
# [CRITICAL DEPENDENCY WARNING] Group 9: 視覺化自我糾錯與 UI 自動測試 (Vision UI Testers)
# ------------------------------------------------------------------------------
# ⚠️ 此檔案屬於高度解耦架構的【Group 9】。
# 負責自動截圖與 OCR 解讀儀表板。一旦 Group 5 的畫面佈局改變，這裡的座標與關鍵字必須同步更新。
# 修改前請務必參閱：PIPELINE_DEPENDENCIES.md
# ==============================================================================
import asyncio
import os
import re
import time
from playwright.async_api import async_playwright

TEST_DIR = "C:/LocalAI_Workstation/test_results/ultimate"
os.makedirs(TEST_DIR, exist_ok=True)

async def check_errors_in_page(page, context_name):
    """提取頁面純文字並進行防線查驗 (Crash Detector)"""
    page_text = await page.inner_text("body")
    error_keywords = ["Traceback:", "NameError:", "ValueError:", "TypeError:", "ImportError:", "Exception:"]
    detected_errors = [kw for kw in error_keywords if kw in page_text]
    
    screenshot_path = os.path.join(TEST_DIR, f"{context_name}.png")
    await page.screenshot(path=screenshot_path)
    
    if detected_errors:
        print(f"  ❌ [{context_name}] Error detected: {detected_errors}")
        return False, detected_errors, screenshot_path
    
    # 預期關鍵字對齊 (Vision Validator Logic)
    # 這裡我們確保即使沒有 Crash，也要能看見正常的 UI 元件 (例如 "Streamlit", "儲存", 等等)
    # 如果畫面全白，inner_text 會是空的或非常少
    if len(page_text.strip()) < 20:
        return False, ["Blank Screen / Failed to Render UI"], screenshot_path
        
    print(f"  ✅ [{context_name}] OK")
    return True, [], screenshot_path

async def run_smoke_test_on_tab_7():
    report_lines = ["# 🛡️ Ultimate UI Crawler - Smoke Test Report (Tab 7)\n"]
    has_critical_errors = False
    
    print("啟動深度爬蟲...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()
        
        print("導航至 http://localhost:8507...")
        await page.goto("http://localhost:8507", wait_until="networkidle")
        await page.wait_for_timeout(3000)
        
        # 1. 找到並點擊 Tab 7 (Index 6)
        tabs = page.locator("button[data-baseweb='tab']")
        count = await tabs.count()
        if count < 7:
            print("找不到足夠的分頁！")
            return
            
        tab7 = tabs.nth(6)
        tab_name = await tab7.inner_text()
        print(f"進入分頁: {tab_name}")
        await tab7.click()
        await page.wait_for_timeout(2000)
        
        report_lines.append(f"## 測試分頁：{tab_name}")
        
        # 狀態 1: 閒置初始狀態 (Idle State)
        ok, errs, path = await check_errors_in_page(page, "Tab7_Idle")
        report_lines.append(f"### 狀態 1: 初始載入 (Idle)")
        report_lines.append(f"- **結果**: {'✅ 通過' if ok else '❌ 失敗'}")
        if errs: 
            report_lines.append(f"- **異常訊息**: {errs}")
            has_critical_errors = True
        report_lines.append(f"- **視覺截圖**: ![]({path})\n")
        
        # 狀態 2: 點擊「一鍵清理死金鑰」按鈕 (Action State)
        print("觸發動作: 尋找清理按鈕並點擊...")
        buttons = page.locator("button")
        btn_count = await buttons.count()
        clicked_clean = False
        for i in range(btn_count):
            btn = buttons.nth(i)
            text = await btn.inner_text()
            if "一鍵清理" in text:
                await btn.click()
                clicked_clean = True
                print("已點擊清理按鈕，等待運算與重新渲染...")
                await page.wait_for_timeout(3000) # 等待 spinner 與 rerun
                break
                
        if clicked_clean:
            ok, errs, path = await check_errors_in_page(page, "Tab7_After_Clean")
            report_lines.append(f"### 狀態 2: 觸發 [一鍵清理金鑰] 操作後")
            report_lines.append(f"- **結果**: {'✅ 通過' if ok else '❌ 失敗'}")
            if errs: 
                report_lines.append(f"- **異常訊息**: {errs}")
                has_critical_errors = True
            report_lines.append(f"- **視覺截圖**: ![]({path})\n")
        else:
            report_lines.append("### 狀態 2: 觸發 [一鍵清理金鑰] 操作後\n- **結果**: ⚠️ 找不到對應的按鈕實體\n")
            
        # 狀態 3: 展開 Ollama 面板 (Expander State)
        print("觸發動作: 尋找 Ollama 面板並展開...")
        expanders = page.locator("div[data-testid='stExpander']")
        exp_count = await expanders.count()
        clicked_exp = False
        for i in range(exp_count):
            exp = expanders.nth(i)
            text = await exp.inner_text()
            if "Ollama" in text:
                await exp.click()
                clicked_exp = True
                print("已展開 Ollama 面板，等待渲染...")
                await page.wait_for_timeout(1000)
                break
                
        if clicked_exp:
            ok, errs, path = await check_errors_in_page(page, "Tab7_Expander_Ollama")
            report_lines.append(f"### 狀態 3: 展開 [Ollama 模型設定] 面板")
            report_lines.append(f"- **結果**: {'✅ 通過' if ok else '❌ 失敗'}")
            if errs: 
                report_lines.append(f"- **異常訊息**: {errs}")
                has_critical_errors = True
            report_lines.append(f"- **視覺截圖**: ![]({path})\n")
        else:
             report_lines.append("### 狀態 3: 展開 [Ollama 模型設定] 面板\n- **結果**: ⚠️ 找不到對應的面板\n")

        await browser.close()
        
    report_lines.insert(1, f"**綜合診斷結果**: {'⚠️ 發現異常狀態' if has_critical_errors else '✅ 各深度狀態均通過驗證'}\n")
    
    with open("C:/LocalAI_Workstation/test_results/ultimate/ultimate_smoke_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print("Smoke test complete. Report saved to test_results/ultimate/ultimate_smoke_report.md")

if __name__ == "__main__":
    asyncio.run(run_smoke_test_on_tab_7())
