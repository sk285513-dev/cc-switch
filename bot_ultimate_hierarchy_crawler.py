# ==============================================================================
# [CRITICAL DEPENDENCY WARNING] Group 6: 外部題庫與法規爬蟲 (External Crawlers)
# ------------------------------------------------------------------------------
# ⚠️ 此檔案屬於高度解耦架構的【Group 6】。
# 抓取下來的資料格式必須完全與本機 DB (Group 1/5) 的解析格式對齊。
# 修改前請務必參閱：PIPELINE_DEPENDENCIES.md
# ==============================================================================
"""
【機制對應宣告】
此腳本 (bot_ultimate_hierarchy_crawler.py) 主要實作了以下視覺測試機制：
- [機制五] 空間感知遍歷之設計 (Semantic DOM Traversal)
- [機制九] 多維度隱藏元件探索之設計 (Hidden Element Exploration)
"""
import asyncio
from playwright.async_api import async_playwright
import os
import shutil
import json

SCREENSHOT_DIR = r"C:\LocalAI_Workstation\Vision_Screenshots_Hierarchy"
DUMP_FILE = r"C:\LocalAI_Workstation\hierarchy_crawler_dump.json"

async def run_hierarchy_crawler():
    print("🚀 [啟動] 階層式功能樹狀遍歷爬蟲 (Hierarchy Traversal) - [機制五/九]")
    
    if os.path.exists(SCREENSHOT_DIR):
        shutil.rmtree(SCREENSHOT_DIR)
    os.makedirs(SCREENSHOT_DIR)
    
    state_dump = []
    total_states = 0
    
    # 嚴格合規：絕對禁用無頭模式，強制 headless=False 彈出實體視窗
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()
        
        try:
            print("⏳ 連線至 Streamlit 伺服器 (Port 8501)...")
            await page.goto("http://localhost:8501", timeout=60000)
            await page.wait_for_selector('button[data-baseweb="tab"]', timeout=30000)
            
            tabs = page.locator('button[data-baseweb="tab"]')
            tab_count = await tabs.count()
            print(f"✅ 成功找到 {tab_count} 個主分頁")
            
            # 第一層：主分頁遍歷
            for t_idx in range(tab_count):
                tabs = page.locator('button[data-baseweb="tab"]')
                if t_idx >= await tabs.count(): break
                await tabs.nth(t_idx).click()
                await asyncio.sleep(1)
                
                tab_name = await tabs.nth(t_idx).inner_text()
                print(f"\n➡️ 進入分頁: {tab_name}，準備深掘子功能樹...")
                
                # 第二層：尋找子頁籤切換器 (st.radio)
                radios = page.locator('input[type="radio"]')
                radio_count = await radios.count()
                
                if radio_count > 0:
                    for r_idx in range(radio_count):
                        radios = page.locator('input[type="radio"]')
                        if r_idx < await radios.count():
                            await radios.nth(r_idx).evaluate("node => node.click()")
                            await asyncio.sleep(1.5) # 等待子頁籤切換渲染
                            
                            total_states += 1
                            file_path = os.path.join(SCREENSHOT_DIR, f"Hierarchy_{total_states:03d}_{tab_name}_Radio_{r_idx}.png")
                            await page.screenshot(path=file_path)
                            page_text = await page.inner_text("body")
                            
                            state_dump.append({
                                "state_id": total_states,
                                "tab": tab_name,
                                "action": f"展開 Radio 子頁籤 {r_idx}",
                                "text": page_text[:2000]
                            })
                            print(f"   📸 [第二層] 成功截取子頁籤 {r_idx} 之渲染畫面")
                            
                # 尋找獨立功能按鈕 (st.button)，這通常是用來生成圖表如心智圖
                # 排除掉主分頁的 tab buttons
                buttons = page.locator('button:not([data-baseweb="tab"])')
                btn_count = await buttons.count()
                
                # 為防組合過多，每頁最多點擊 10 個核心功能按鈕
                for b_idx in range(min(10, btn_count)):
                    buttons = page.locator('button:not([data-baseweb="tab"])')
                    if b_idx < await buttons.count():
                        btn_text = await buttons.nth(b_idx).inner_text()
                        if btn_text.strip() == "":
                            continue
                            
                        # 點擊該功能鍵
                        try:
                            await buttons.nth(b_idx).click()
                            print(f"   ▶️ [第三層] 觸發功能鍵: {btn_text}")
                            
                            # 等待圖表或資料流渲染 (Spinner)
                            await asyncio.sleep(2)
                            
                            total_states += 1
                            file_path = os.path.join(SCREENSHOT_DIR, f"Hierarchy_{total_states:03d}_{tab_name}_Btn_{b_idx}.png")
                            await page.screenshot(path=file_path)
                            page_text = await page.inner_text("body")
                            
                            state_dump.append({
                                "state_id": total_states,
                                "tab": tab_name,
                                "action": f"觸發功能鍵: {btn_text}",
                                "text": page_text[:2000]
                            })
                            
                            if "Traceback" in page_text or "Exception" in page_text:
                                print(f"      ❌ 警告：觸發 {btn_text} 後發生崩潰！")
                            else:
                                print(f"      ✅ 圖表/內容已成功渲染！(擷取至 {file_path})")
                                
                        except Exception as btn_e:
                            print(f"      ⚠️ 功能鍵點擊失敗: {btn_e}")
                            
            print(f"\n🎉 階層遍歷完成！共取得 {total_states} 張真實視窗大功能模組快照！")
            
        except Exception as e:
            print(f"💥 測試異常中斷: {e}")
        finally:
            await browser.close()
            
    with open(DUMP_FILE, "w", encoding="utf-8") as f:
        json.dump(state_dump, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    asyncio.run(run_hierarchy_crawler())
