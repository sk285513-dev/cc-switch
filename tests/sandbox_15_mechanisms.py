import asyncio
from playwright.async_api import async_playwright, Page
import os
import json
import itertools
import psutil
import time
import collections

SCREENSHOT_DIR = r"C:\LocalAI_Workstation\Vision_Screenshots_Tree"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
STATE_DUMP_FILE = os.path.join(SCREENSHOT_DIR, "state_dump.json")

# Mechanism 3: Crash detection
async def check_crash(page: Page, state_id: str):
    page_text = await page.inner_text("body")
    error_keywords = ["Traceback", "Exception:", "st.error", "IndexError"]
    for kw in error_keywords:
        if kw in page_text:
            print(f"   [警告] 偵測到系統崩潰紅字: {kw}")
            # Mechanism 6: Disk I/O Isolation (saving directly)
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f"CRASH_{state_id}.png"))
            return True
    return False

# Mechanism 9: Hidden Element Exploration
async def expand_all(page: Page):
    expanders = await page.locator('div[data-testid="stExpander"]').all()
    for exp in expanders:
        try:
            await exp.click(force=True)  # 強制觸發底層隱藏元素
        except Exception:
            pass

# Mechanism 13: Async Spinner Synchronization
async def wait_spinner(page: Page):
    spinner = page.locator('.stSpinner')
    if await spinner.count() > 0:
        await spinner.wait_for(state="detached", timeout=60000)
    if await page.locator(".stMarkdown").count() == 0:
        print("   [警告] 無 Markdown 產出")

async def run_sandbox_tests():
    state_dump = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        page = await context.new_page()

        # Mechanism 14: Resource Telemetry start
        process = psutil.Process(os.getpid())
        start_time = time.perf_counter()

        # Mechanism 2: Event-Driven DOM Synchronization
        print("[測試] 導航至測試環境")
        await page.goto("http://localhost:8502", timeout=60000)
        await page.wait_for_selector('button[data-baseweb="tab"]', state="visible", timeout=30000)
        
        tabs = await page.locator('button[data-baseweb="tab"]').all()
        
        # --- 測試首頁 ---
        print("\n[目錄] 測試分頁 1: 首頁 (防爆矩陣與崩潰)")
        await tabs[0].click()
        await page.wait_for_load_state("networkidle")
        
        # Mechanism 8: Combinatorial explosion prevention
        combo_matrix = list(itertools.product([True, False], repeat=2))[:2]  # 降維只測兩種
        
        for idx, (check_a, check_b) in enumerate(combo_matrix):
            state_id = f"TAB1_COMBO_{idx}"
            truth_table = {"check_lawyer": check_a, "check_judge": check_b}
            crash_detected = False
            
            # Mechanism 4: RAII try-except-finally
            try:
                if check_a: await page.locator('label:has-text("特徵 A (check_lawyer)")').click()
                if check_b: await page.locator('label:has-text("特徵 B (check_judge)")').click()
                
                await page.locator('button:has-text("啟動一鍵批次研讀")').click()
                # 修正：等待成功訊息文字出現
                await page.wait_for_selector('text="研讀啟動中..."', state="visible", timeout=5000)
                
            except Exception as e:
                print(f"操作異常: {e}")
            finally:
                crash_detected = await check_crash(page, state_id)
                if not crash_detected:
                    await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f"{state_id}.png"))
                
                # Mechanism 7 & 10: Semantic Assertion Decoupling & Traceability Logging
                state_dump.append({
                    "state_id": state_id,
                    "ui_truth_table": truth_table,
                    "crash_detected": crash_detected,
                    "dom_text": (await page.inner_text("body"))[:2000]
                })

        # 測試崩潰按鈕
        print("\n[目錄] 測試崩潰按鈕")
        state_id = "TAB1_CRASH"
        try:
            await page.locator('button:has-text("模擬系統崩潰")').click()
            await page.wait_for_timeout(1000) # 給 Streamlit 反應時間
        except Exception:
            pass
        finally:
            crash_detected = await check_crash(page, state_id)
            state_dump.append({
                "state_id": state_id,
                "ui_truth_table": {"crash_btn": True},
                "crash_detected": crash_detected,
                "dom_text": (await page.inner_text("body"))[:2000]
            })

        # Mechanism 11: Forced State Reset
        print("\n[目錄] 狀態重置 (進入分頁3)")
        tabs = await page.locator('button[data-baseweb="tab"]').all()
        await tabs[2].click()
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1000)
        
        # Mechanism 5: Semantic DOM Traversal
        print("\n[目錄] 進入分頁 2: 知識餵養")
        tabs = await page.locator('button[data-baseweb="tab"]').all()
        await tabs[1].click()
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1000)

        await expand_all(page)

        # Mechanism 12: High-Fidelity Synthetic Events
        state_id = "TAB2_QUERY"
        try:
            text_area = page.locator('textarea').first
            await text_area.wait_for(state="visible", timeout=10000)
            await text_area.fill("模擬真人輸入：甲打傷乙")
            await text_area.blur()  # 觸發 React Synthetic Event
            
            # Submitting query
            await page.locator('button:has-text("提交查詢")').click()
            
            # Mechanism 13: Async Spinner Synchronization
            await wait_spinner(page)
            
        except Exception as e:
            print(f"操作異常: {e}")
        finally:
            crash_detected = await check_crash(page, state_id)
            if not crash_detected:
                await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f"{state_id}.png"))
                
            state_dump.append({
                "state_id": state_id,
                "ui_truth_table": {"query": "模擬真人輸入：甲打傷乙"},
                "crash_detected": crash_detected,
                "dom_text": (await page.inner_text("body"))[:2000]
            })

        await browser.close()
        
        with open(STATE_DUMP_FILE, "w", encoding="utf-8") as f:
            json.dump(state_dump, f, ensure_ascii=False, indent=2)

        # Mechanism 14: Resource Telemetry end
        latency = time.perf_counter() - start_time
        ram_mb = process.memory_info().rss / (1024 * 1024)
        print(f"\n[遙測] 耗時: {latency:.2f}s | RAM: {ram_mb:.1f} MB")
        
        # Mechanism 15: Multidimensional Error Heatmap Analysis
        crash_counts = collections.defaultdict(int)
        total_counts = collections.defaultdict(int)
        
        for state in state_dump:
            for feature, val in state["ui_truth_table"].items():
                if type(val) == bool and val: # 只統計布林值
                    total_counts[feature] += 1
                    if state["crash_detected"]:
                        crash_counts[feature] += 1
                        
        print("\n--- 錯誤熱力圖分析 ---")
        if not total_counts:
            print("無真值表特徵。")
        for feature in total_counts:
            rate = crash_counts[feature] / total_counts[feature]
            print(f"特徵 [{feature}] 導致崩潰機率: {rate:.2%}")
        print("------------------------")

if __name__ == "__main__":
    asyncio.run(run_sandbox_tests())
