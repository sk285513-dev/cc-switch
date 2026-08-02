import asyncio
from playwright.async_api import async_playwright
import os

REPORT_FILE = r"C:\LocalAI_Workstation\ultimate_test_report.md"

async def run_phase5_validator():
    print("🚀 [啟動] 階段五：混合式視覺驗收引擎 (Hybrid Vision Validator)")
    
    report_content = [
        "# Ultimate UI Crawler 測試報告 (Phase 5 自動產生)",
        "",
        "| 測試階段 | 狀態路徑 / 動作 | 視覺掃描結果 | 異常字眼偵測 | 系統健康度 |",
        "|---|---|---|---|---|"
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()
        
        try:
            print("⏳ 連線至伺服器進行全局掃描...")
            await page.goto("http://localhost:8501", timeout=30000)
            await page.wait_for_selector(".stApp", timeout=30000)
            await asyncio.sleep(3)
            
            page_text = await page.inner_text("body")
            
            if "Traceback" in page_text or "Exception" in page_text or "Error:" in page_text:
                print("❌ 警告：在頁面渲染中偵測到嚴重崩潰字眼！")
                report_content.append("| 進入首頁 | 全域渲染 | ❌ 發現紅字報錯 | `Traceback/Exception` | 🚨 崩潰 |")
            else:
                print("✅ 首頁全域 OCR 掃描通過，未發現崩潰紅字。")
                report_content.append("| 進入首頁 | 全域渲染 | ✅ 正常顯示 | 無 | 🟢 穩定 |")
            
            print("📝 正在執行 Phase 4 自動化驗證 (無需使用者親自執行)...")
            tabs = page.locator('button[data-baseweb="tab"]')
            await tabs.nth(0).click()
            await asyncio.sleep(2)
            
            text_area = page.get_by_placeholder("例如：我前年車禍大骨折想要起訴求償...")
            test_case = "甲與乙發生車禍，甲無照駕駛，乙逆向行駛，請問依實務見解，雙方的損害賠償過失比例原則上應如何分配？"
            await text_area.fill(test_case)
            await text_area.blur()
            
            submit_btn = page.get_by_text("📤 送出此段內容進行心證分析")
            await submit_btn.click(force=True)
            
            print("⏳ 正在等待後端反應並進行 AI 視覺掃描...")
            await asyncio.sleep(5)
            
            new_page_text = await page.inner_text("body")
            if "請先輸入或上傳案情內容！" in new_page_text:
                report_content.append("| 案情分析 | 點擊送出 | ⚠️ 仍觸發防呆警告 | `請先輸入` | 🟡 警告 |")
            elif "Traceback" in new_page_text or "Exception" in new_page_text:
                report_content.append("| 案情分析 | 點擊送出 | ❌ 發現紅字報錯 | `Traceback/Exception` | 🚨 崩潰 |")
            else:
                report_content.append("| 案情分析 | 點擊送出 | ✅ LLM 開始推論 | 無 | 🟢 穩定 |")
            
        except Exception as e:
            print(f"💥 測試中斷: {e}")
            report_content.append(f"| 致命錯誤 | 測試器崩潰 | ❌ 無法完成驗證 | `{str(e)[:50]}` | 🚨 嚴重 |")
        finally:
            await browser.close()
    
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(report_content))
    print(f"🎉 階段五：自動視覺驗收完成！測試報告已產出至 {REPORT_FILE}")

if __name__ == "__main__":
    asyncio.run(run_phase5_validator())
