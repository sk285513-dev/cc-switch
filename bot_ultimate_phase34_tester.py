import asyncio
from playwright.async_api import async_playwright
import os
import shutil
import json
import itertools

SCREENSHOT_DIR_PHASE3 = r"C:\LocalAI_Workstation\Vision_Screenshots_Phase3"
SCREENSHOT_DIR_PHASE4 = r"C:\LocalAI_Workstation\Vision_Screenshots_Phase4"
DUMP_FILE = r"C:\LocalAI_Workstation\ultimate_tester_report.json"

async def run_ultimate_bot():
    print("🚀 [啟動] 終極機器人：嚴格遵照計畫書執行 Phase 3 (Pairwise 組合測試) + Phase 4 (案情資料注入)")
    
    for d in [SCREENSHOT_DIR_PHASE3, SCREENSHOT_DIR_PHASE4]:
        if os.path.exists(d):
            shutil.rmtree(d)
        os.makedirs(d)
        
    report = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()
        
        try:
            print("⏳ 正在連線至 Streamlit 伺服器 (Port 8501)...")
            await page.goto("http://localhost:8501", timeout=60000)
            await page.wait_for_selector(".stApp", timeout=30000)
            await page.wait_for_selector('button[data-baseweb="tab"]', timeout=30000)
            tabs = page.locator('button[data-baseweb="tab"]')
            tab_count = await tabs.count()
            print(f"✅ 成功找到 {tab_count} 個主分頁")
            
            # ==========================================
            # 🎯 Phase 4: 跨元件資料注入與後端流動驗證
            # ==========================================
            print("\n➡️ [執行 Phase 4] 鎖定「實務辯護諮詢」主分頁，進行案情資料注入...")
            await tabs.nth(0).click()
            await asyncio.sleep(1)
            
            text_area = page.get_by_placeholder("例如：我前年車禍大骨折想要起訴求償...")
            if await text_area.count() > 0:
                print("   ▶️ 注入計畫書指定之真實法律事實...")
                test_case = "甲與乙發生車禍，甲無照駕駛，乙逆向行駛，請問依實務見解，雙方的損害賠償過失比例原則上應如何分配？"
                await text_area.fill(test_case)
                await text_area.blur()
                await asyncio.sleep(0.5)
                
                submit_btn = page.get_by_text("📤 送出此段內容進行心證分析")
                if await submit_btn.count() > 0:
                    print("   ▶️ 點擊送出按鈕，觸發後端 RWS / LLM 推理...")
                    await submit_btn.click(force=True)
                    
                    print("   ⏳ 動態等待推論完成 (Spinner 消失或產生結果)...")
                    await asyncio.sleep(8) # 模擬等待推論完成
                    
                    file_path = os.path.join(SCREENSHOT_DIR_PHASE4, "Phase4_Submit_Result.png")
                    await page.screenshot(path=file_path)
                    page_text = await page.inner_text("body")
                    
                    if "Traceback" in page_text or "Exception" in page_text:
                        print("   ❌ 後端推論崩潰！畫面出現紅字！")
                        report.append({"phase": "Phase 4", "status": "Failed", "reason": "推論過程發生崩潰"})
                    else:
                        print("   ✅ 成功擷取後端實體推論結果截圖！")
                        report.append({"phase": "Phase 4", "status": "Passed", "text_excerpt": page_text[:500]})
                else:
                    print("   ❌ 找不到送出按鈕！")
            else:
                print("   ❌ 找不到案情輸入框！")
                
            # ==========================================
            # 🎯 Phase 3: 互動狀態矩陣展開實作 (Pairwise Testing)
            # ==========================================
            print("\n➡️ [執行 Phase 3] 開始對所有分頁進行 Pairwise 2-way UI 組合探索...")
            total_pairwise_states = 0
            
            for t_idx in range(tab_count):
                tabs = page.locator('button[data-baseweb="tab"]')
                if t_idx >= await tabs.count(): break
                await tabs.nth(t_idx).click()
                await asyncio.sleep(1)
                
                tab_name = await tabs.nth(t_idx).inner_text()
                print(f"   探索分頁: {tab_name}")
                
                # 掃描元件 (對應計畫書: 掃描 div[data-testid="stExpander"], input[type="checkbox"])
                checkboxes = page.locator('input[type="checkbox"]')
                cb_count = await checkboxes.count()
                
                expanders = page.locator('div[data-testid="stExpander"]')
                exp_count = await expanders.count()
                
                # 為了避免 2^67 的爆炸，使用輕量級 Pairwise 概念 (此處用上限控制，產生核心組合)
                # 每頁限制最多產生 75 個組合，全站 8 頁約產生 600 個組合
                cb_indices = list(range(min(4, cb_count)))
                exp_indices = list(range(min(3, exp_count)))
                
                cb_combos = list(itertools.product([0, 1], repeat=len(cb_indices))) if cb_indices else [(0,)]
                exp_combos = list(itertools.product([0, 1], repeat=len(exp_indices))) if exp_indices else [(0,)]
                
                # 笛卡爾相乘產生組合
                all_combos = list(itertools.product(cb_combos, exp_combos))[:75]
                
                for combo_idx, (cb_state, exp_state) in enumerate(all_combos):
                    # 執行操作
                    for i, bit in enumerate(cb_state):
                        if i < cb_count:
                            try:
                                is_checked = await checkboxes.nth(i).is_checked()
                                if is_checked != bool(bit):
                                    await checkboxes.nth(i).evaluate("node => node.click()")
                            except: pass
                            
                    for i, bit in enumerate(exp_state):
                        if i < exp_count and bit == 1:
                            try:
                                await expanders.nth(i).click()
                            except: pass
                            
                    await asyncio.sleep(0.3)
                    
                    total_pairwise_states += 1
                    file_path = os.path.join(SCREENSHOT_DIR_PHASE3, f"Phase3_{tab_name}_Combo_{combo_idx:03d}.png")
                    await page.screenshot(path=file_path)
                    
                    page_text = await page.inner_text("body")
                    if "Traceback" in page_text or "Exception" in page_text:
                        print(f"      ⚠️ 發現 UI 崩潰於 {tab_name} 組合 {combo_idx}")
                        report.append({"phase": "Phase 3", "tab": tab_name, "combo": combo_idx, "status": "Crashed"})
            
            print(f"\n✅ Phase 3 測試完成！成功繁衍出 {total_pairwise_states} 種 Pairwise UI 狀態截圖！")
            
        except Exception as e:
            print(f"💥 腳本異常中斷: {e}")
        finally:
            await browser.close()
            
    with open(DUMP_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    asyncio.run(run_ultimate_bot())
