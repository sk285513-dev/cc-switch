import asyncio
from playwright.async_api import async_playwright
import os
import shutil
import itertools

SCREENSHOT_DIR = r"C:\LocalAI_Workstation\Vision_Screenshots_Phase3"

HIERARCHY = {
    0: {"name": "實務辯護諮詢", "subtabs": ["RWS 證據看板", "事件關係圖"]},
    1: {"name": "知識餵養", "subtabs": []},
    2: {"name": "法律個案管理", "subtabs": []},
    3: {"name": "教材檢索與定位", "subtabs": []},
    4: {"name": "司法官自我養成", "subtabs": []},
    5: {"name": "訴訟書狀起草", "subtabs": []},
    6: {"name": "系統與時效工具", "subtabs": []},
    7: {"name": "Antigravity 控制台", "subtabs": ["與 Antigravity 即時對話", "背景運作與工具軌跡"]},
}

# 輕量級的 Pairwise (2-way) 測試矩陣產生器
# 為避免需要安裝外部套件 (如 allpairspy)，這裡實作一個精簡版的成對組合取樣器。
# 若元件數量 (N) 很少，直接傳回所有組合；若數量多，則取所有 2-way 排列的最小覆蓋集。
def generate_pairwise_matrix(n_elements):
    if n_elements == 0:
        return []
    if n_elements <= 3:
        # 3個以內直接全展開 (2^3 = 8種)
        return list(itertools.product([False, True], repeat=n_elements))
    
    # 對於超過 3 個元件，我們生成一組能夠覆蓋「任意兩個元件組合」的輕量級矩陣
    # 這裡採用簡化的輪替矩陣(Orthogonal Array 近似)，將狀態壓縮到約 O(N) 數量級
    matrix = []
    # 1. 全關
    matrix.append([False] * n_elements)
    # 2. 全開
    matrix.append([True] * n_elements)
    # 3. 逐一開啟 (確保每一對都有 True-False 與 False-True 的組合)
    for i in range(n_elements):
        row = [False] * n_elements
        row[i] = True
        matrix.append(row)
    # 4. 相鄰成對開啟 (涵蓋更多的 True-True)
    for i in range(n_elements - 1):
        row = [False] * n_elements
        row[i] = True
        row[i+1] = True
        matrix.append(row)
    
    # 去除重複
    unique_matrix = []
    for row in matrix:
        if row not in unique_matrix:
            unique_matrix.append(row)
    return unique_matrix

async def run_vision_crawler():
    print("🚀 [啟動] 階段三：學術級 Pairwise 狀態展開爬蟲")
    
    if os.path.exists(SCREENSHOT_DIR):
        shutil.rmtree(SCREENSHOT_DIR)
    os.makedirs(SCREENSHOT_DIR)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()
        
        try:
            print("⏳ 正在連線至 Streamlit 伺服器...")
            await page.goto("http://localhost:8501", timeout=60000)
            await page.wait_for_selector(".stApp", timeout=30000)
            
            await page.wait_for_selector('button[data-baseweb="tab"]', timeout=60000)
            await asyncio.sleep(2)
            
            main_tabs = await page.locator('button[data-baseweb="tab"]').all()
            if len(main_tabs) < 8:
                print("❌ [錯誤] 找不到主分頁。")
                return
                
            main_tabs = main_tabs[:8]
            
            # 為了控制總時長不至於太誇張 (600 張圖若每張 2 秒要 20 分鐘)
            # 我們在此階段「重點展示」其中 3 個分頁的 Pairwise 展開。
            test_indices = [0, 1, 7] # 只挑選 實務辯護、知識餵養、控制台 做深度的 Pairwise 示範
            
            for i in test_indices:
                main_tab = main_tabs[i]
                tab_info = HIERARCHY.get(i)
                main_name = tab_info["name"]
                
                print(f"\\n➡️ 正在展開主分頁: {main_name}")
                await main_tab.click()
                await asyncio.sleep(2)
                
                # 尋找這個分頁畫面上的所有可互動 Checkbox
                checkboxes = await page.locator('input[type="checkbox"]').all()
                n_checkboxes = len(checkboxes)
                
                print(f"   🔍 掃描到 {n_checkboxes} 個可互動 Checkbox 元件。")
                if n_checkboxes > 0:
                    # 透過演算法產生 Pairwise 測試矩陣
                    test_matrix = generate_pairwise_matrix(n_checkboxes)
                    print(f"   📊 成功將 $2^{{{n_checkboxes}}}$ 全排列壓縮至 {len(test_matrix)} 種 Pairwise 測試路徑！")
                    
                    for path_idx, state_row in enumerate(test_matrix):
                        print(f"      ▶️ 執行路徑 {path_idx+1}: {state_row}")
                        
                        # 依照矩陣狀態點擊 Checkbox
                        for cb_idx, target_state in enumerate(state_row):
                            cb = checkboxes[cb_idx]
                            is_checked = await cb.is_checked()
                            if is_checked != target_state:
                                await cb.evaluate("node => node.click()")
                                
                        await asyncio.sleep(1) # 等待 UI 重新渲染
                        
                        # 拍攝該狀態的實體截圖
                        file_path = os.path.join(SCREENSHOT_DIR, f"0{i+1}_{main_name}_Pairwise_Path{path_idx+1:02d}.png")
                        await page.screenshot(path=file_path)
                        print(f"      📸 已留存狀態截圖: {file_path}")
                        
                else:
                    print(f"   ⚠️ 該分頁無 Checkbox，略過狀態擴張。")
                
        except Exception as e:
            print(f"💥 測試中斷: {e}")
        finally:
            await browser.close()
            print("\\n🎉 階段三：Pairwise 狀態展開測試完成！")

if __name__ == "__main__":
    asyncio.run(run_vision_crawler())
