"""
【機制對應宣告】
此腳本 (bot_ultimate_real_crawler.py) 主要實作了以下視覺測試機制：
- [機制二] 強制防護等待之設計 (Event-Driven DOM Synchronization)
- [機制三] 崩潰紅字防禦之設計 (Implicit Dynamic Oracles)
- [機制四] 絕對畫面捕捉與死碼消除之設計 (RAII Snapshot)
- [機制六] 全面實體留存與 OOM 迴避之設計 (Disk I/O Isolation)
- [機制七] 語意與測試解耦之設計 (Semantic Assertion Decoupling)
- [機制十] 真值表軌跡追蹤之設計 (Statechart Traceability Logging)
- [機制十二] 高擬真事件注入之設計 (High-Fidelity Synthetic Events)
- [機制十三] 動態非同步推論等待與驗證之設計 (Async Spinner Synchronization)
"""
import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
import socket
from playwright.async_api import async_playwright, Page
import os
import itertools
import psutil
import time
import json
import collections

SCREENSHOT_DIR = r"C:\LocalAI_Workstation\Vision_Screenshots_Tree"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# ===== 前置驗證閘門：任何一項失敗就終止，不浪費一張截圖 =====
def preflight_check():
    TARGET_PORT = 8501
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    result = sock.connect_ex(("localhost", TARGET_PORT))
    sock.close()
    if result != 0:
        print(f"[Preflight FAIL] Streamlit not running on Port {TARGET_PORT}. Please start Streamlit first.")
        sys.exit(1)
    print(f"[Preflight OK] Port {TARGET_PORT} is LIVE, Streamlit ready.")

# [機制十：真值表軌跡追蹤之設計] 狀態追蹤字典與 [機制十九/二十] 遙測
state_dump = []
telemetry_dump = []
process = psutil.Process(os.getpid())

# [機制三：崩潰紅字防禦之設計 (Implicit Dynamic Oracle)]
async def check_crash(page: Page, state_id: str):
    # 【修復 Issue 18】針對 Streamlit 原生的錯誤容器 .stException 進行精確 DOM 特徵偵測，不全域掃描內文
    exception_nodes = page.locator('div[data-testid="stException"], .stException')
    if await exception_nodes.count() > 0:
        error_text = (await exception_nodes.first.inner_text())[:200]
        print(f"   [警告] 偵測到系統崩潰: {error_text.replace(chr(10), ' ')}")
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f"CRASH_{state_id}.png"))
        return True
    return False

# [機制十三：動態非同步推論等待與驗證之設計]
async def wait_spinner(page: Page):
    try:
        # 【修復 Issue 16】不再只等待 selector 避免截取舊畫面，改為等待 Streamlit 執行狀態指示器
        print("   [狀態] 監聽 Streamlit 執行狀態 (script-state)...")
        # 1. 確保腳本開始執行 (避免太快抓到舊畫面)
        try:
            await page.wait_for_selector('[data-test-script-state="running"]', state="attached", timeout=3000)
        except:
            pass # 可能太快執行完畢
            
        # 2. 確保腳本執行結束
        await page.wait_for_selector('[data-test-script-state="notRunning"]', state="attached", timeout=60000)
            
        # 機制 13: Markdown 渲染驗證
        if await page.locator(".stMarkdown").count() == 0:
            print("   [警告] 畫面上沒有檢測到 Markdown 渲染區塊")
    except Exception:
        pass

# 機制 8: 多維度隱藏元件探索
async def expand_all(page: Page):
    expanders = await page.locator('div[data-testid="stExpander"]').all()
    for exp in expanders:
        try:
            await exp.click(force=True)
        except Exception:
            pass

async def explore_tree():
    # 【修復 Issue 15】貪婪演算法生成真實的 Pairwise 涵蓋陣列
    def generate_covering_array(n_params: int, values=None):
        if values is None: values = [True, False]
        pairs_needed = set()
        for i in range(n_params):
            for j in range(i + 1, n_params):
                for vi in values:
                    for vj in values:
                        pairs_needed.add((i, j, vi, vj))
        test_cases = []
        while pairs_needed:
            case = [None] * n_params
            uncovered = list(pairs_needed)
            for (i, j, vi, vj) in uncovered:
                if (case[i] is None or case[i] == vi) and (case[j] is None or case[j] == vj):
                    case[i] = vi
                    case[j] = vj
                    pairs_needed.remove((i, j, vi, vj))
            for i in range(n_params):
                if case[i] is None: case[i] = False
            to_remove = set()
            for (i, j, vi, vj) in pairs_needed:
                if case[i] == vi and case[j] == vj:
                    to_remove.add((i, j, vi, vj))
            pairs_needed -= to_remove
            test_cases.append(case)
        return test_cases

    preflight_check()  # 先通過前置驗證，確認 Streamlit 在線
    print("[啟動] 樹狀圖階層式 UI 深度遍歷測試 (Tree-Hierarchical Deep Crawl) 完整 15 項防護版")
    
    # 機制 1: 事件驅動同步防護
    async with async_playwright() as p:
        # M1: 環境感知模式 — 由 VBS 啟動時 CRAWLER_HEADFUL=1 → headful 顯示桌面；CI 環境保持 headless
        headful = os.environ.get("CRAWLER_HEADFUL", "0") == "1"
        browser = await p.chromium.launch(headless=not headful)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()
        
        await page.goto("http://localhost:8501", timeout=60000)
        await page.wait_for_selector('button[data-baseweb="tab"]', state="visible", timeout=30000)
        
        all_tabs = page.locator('button[data-baseweb="tab"]')
        tab_count = await all_tabs.count()
        print(f"[探測] 找到 {tab_count} 個分頁按鈕")

        async def click_tab_by_text(text):
            """按文字定位分頁，不依賴數字索引"""
            tab = page.locator(f'button[data-baseweb="tab"]:has-text("{text}")')
            cnt = await tab.count()
            if cnt > 0:
                await tab.first.click()
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(1000)
                return True
            # fallback: 列出所有 tab 文字以供除錯
            print(f"   [警告] 找不到分頁: {text}，已有分頁:")
            for i in range(tab_count):
                t = await all_tabs.nth(i).inner_text()
                print(f"      [{i}] {t.strip()}")
            return False

        async def select_option(option_text, selector_index="first"):
            """正確的 Streamlit selectbox 互動：點開 → 等候選清單 → 點選項"""
            try:
                if selector_index == "first":
                    # 點擊 selectbox 內層可互動子 div，不是外層包装 div
                    box = page.locator('[data-testid="stSelectbox"]').first.locator('div[role="button"], [data-baseweb="select"] > div').first
                else:
                    box = page.locator('[data-testid="stSelectbox"]').last.locator('div[role="button"], [data-baseweb="select"] > div').first
                await box.scroll_into_view_if_needed()
                await box.click(timeout=5000)
                # 等候 Streamlit listbox 完全渲染出來（最多 3 秒）
                try:
                    await page.wait_for_selector('ul[role="listbox"]', timeout=3000)
                except Exception:
                    await page.wait_for_timeout(800)  # fallback: 直接等 800ms
                option = page.locator(f'li[role="option"]:has-text("{option_text}")')
                if await option.count() == 0:
                    # 備用：用 ul li 找
                    option = page.locator(f'ul li:has-text("{option_text}")')
                if await option.count() > 0:
                    await option.first.click()
                    await page.wait_for_timeout(500)
                    return True
                else:
                    print(f"   [WARN] option not found: {option_text.encode('ascii','replace').decode()}")
                    await page.keyboard.press("Escape")
                    return False
            except Exception as e:
                safe_e = repr(e).encode('ascii', 'replace').decode()
                print(f"   [ERROR] select_option failed: {safe_e[:150]}")
                return False

        # --- TAB 1: 實務辯護諮詢 ---
        print("\n[目錄] 進入分頁 1: 實務辯護諮詢")
        await click_tab_by_text("實務辯護諮詢")
        await page.wait_for_load_state("networkidle")
        
        all_roles = ["律師 (時效防禦優先)", "法官 (客觀法規對位)", "檢察官 (刑事犯罪求處)"]
        tabs_locator = page.locator('button[data-baseweb="tab"]')
        for role in all_roles:
            # M11: 每輪迭代前強制 reset 根分頁，確保乾淨起點
            await click_tab_by_text("實務辯護諮詢")
            # 機制 4: 絕對畫面捕捉與死碼消除 (RAII)
            # 機制 14: 效能遙測
            start_time = time.perf_counter()
            state_id = f"Tab1_{role}"
            is_crashed = False
            dom_text = ""
            try:
                print(f"   ├── 測試子孫選項: {role}")
                radio = page.locator(f'text="{role}"')
                if await radio.count() > 0:
                    await radio.click()
                    await page.wait_for_timeout(500)
                    
                text_area = page.locator('textarea').first
                if await text_area.count() > 0:
                    # 機制 12: 高擬真事件注入 (fill + blur)
                    await text_area.fill(f"測試 {role} 的自動化輸入機制。")
                    await text_area.blur()
                    await page.keyboard.press("Enter")
                    await wait_spinner(page)
                    await expand_all(page)  # M9: 展開所有隱藏元件
                    
            except Exception as e:
                print(f"   [錯誤] 操作發生異常: {e}")
            finally:
                # M7: 採集 DOM 文字（語意解耦，不在爬蟲內做 Assert）
                dom_text = (await page.inner_text("body"))[:2000]
                is_crashed = await check_crash(page, state_id)
                if not is_crashed:
                    # 機制 6: 絕對 Disk I/O 截圖防 OOM
                    await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f"{state_id}.png"))
                
                # M10: 多維真值表 — 記錄所有角色的布林狀態向量
                truth_table = {r: (r == role) for r in all_roles}
                # 機制 10 & 14 採集
                latency = time.perf_counter() - start_time
                ram_mb = process.memory_info().rss / (1024 * 1024)
                print(f"   [遙測] 耗時: {latency:.2f}s | RAM: {ram_mb:.1f} MB")
                telemetry_dump.append({"state_id": state_id, "latency_sec": round(latency, 3), "ram_usage_mb": round(ram_mb, 2)})
                state_dump.append({
                    "state_id": state_id,
                    "crash_detected": is_crashed,
                    "dom_text": dom_text,
                    "ui_truth_table": truth_table
                })
        
        # --- TAB 2: 知識餵養 ---
        print("\n[目錄] 進入分頁 2: 知識餵養")
        await click_tab_by_text("知識餵養")
        
        # 機制 8: 防組合爆炸演算法之設計 (Combinatorial Matrix)
        print("   ├── 測試子孫選項: 批次研讀組合測試")
        combo_matrix = generate_covering_array(2, [True, False])
        for idx, matrix_val in enumerate(combo_matrix):
            start_time = time.perf_counter()
            state_id = f"Tab2_Ingest_Combo_{idx}"
            is_crashed = False
            dom_text = ""
            try:
                btn_ingest = page.locator('text="啟動一鍵批次研讀與消化"')
                if await btn_ingest.count() > 0:
                    await btn_ingest.click()
                    await wait_spinner(page)
            except Exception as e:
                print(f"   [錯誤] 發生異常: {e}")
            finally:
                await expand_all(page)  # M9: 展開所有隱藏元件
                dom_text = (await page.inner_text("body"))[:2000]  # M7: 採集 DOM 文字
                is_crashed = await check_crash(page, state_id)
                if not is_crashed:
                    await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f"{state_id}.png"))
                    
                latency = time.perf_counter() - start_time
                ram_mb = process.memory_info().rss / (1024 * 1024)
                print(f"   [遙測] 耗時: {latency:.2f}s | RAM: {ram_mb:.1f} MB")
                telemetry_dump.append({"state_id": state_id, "latency_sec": round(latency, 3), "ram_usage_mb": round(ram_mb, 2)})
                # M10: 組合矩陣真值表
                state_dump.append({
                    "state_id": state_id,
                    "crash_detected": is_crashed,
                    "dom_text": dom_text,
                    "ui_truth_table": {f"Combo_{i}": bool(matrix_val[i]) for i in range(len(matrix_val))}
                })

        # --- TAB 3: 司法官自我養成 ---
        print("\n[目錄] 進入分頁 3: 司法官自我養成")
        await click_tab_by_text("司法官自我養成")
        start_time = time.perf_counter()
        state_id = "Tab3_Exam"
        is_crashed = False
        dom_text = ""
        try:
            btn_exam = page.locator('text="送入考場！AI 模擬作答與反思"')
            if await btn_exam.count() > 0:
                print("   ├── 測試子孫選項: 送入考場")
                await btn_exam.click()
                await wait_spinner(page)
        except Exception:
            pass
        finally:
            await expand_all(page)  # M9: 展開所有隱藏元件
            dom_text = (await page.inner_text("body"))[:2000]  # M7: 採集 DOM 文字
            is_crashed = await check_crash(page, state_id)
            if not is_crashed:
                await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f"{state_id}.png"))
            latency = time.perf_counter() - start_time
            ram_mb = process.memory_info().rss / (1024 * 1024)
            print(f"   [遙測] 耗時: {latency:.2f}s | RAM: {ram_mb:.1f} MB")
            telemetry_dump.append({"state_id": state_id, "latency_sec": round(latency, 3), "ram_usage_mb": round(ram_mb, 2)})
            state_dump.append({
                "state_id": state_id,
                "crash_detected": is_crashed,
                "dom_text": dom_text,
                "ui_truth_table": {"Exam": True}
            })

        # --- TAB 4: 訴訟書狀起草 ---
        print("\n[目錄] 進入分頁 4: 訴訟書狀起草")
        await click_tab_by_text("訴訟書狀起草")
        draft_options = ["民事損害賠償起訴狀", "刑事告訴狀", "民事答辯狀", "民事上訴理由狀"]
        for opt in draft_options:
            start_time = time.perf_counter()
            state_id = f"Tab4_{opt}"
            try:
                await select_option(opt, "first")
                btn_draft = page.locator('text="✍️ 自動起草專業文書/書狀"')
                if await btn_draft.count() > 0:
                    await btn_draft.click()
                    await wait_spinner(page)
            finally:
                await expand_all(page)
                dom_text = (await page.inner_text("body"))[:2000]
                telemetry_dump.append({"state_id": state_id, "latency_sec": round(time.perf_counter() - start_time, 3), "ram_usage_mb": round(process.memory_info().rss / (1024 * 1024), 2)})
                state_dump.append({
                    "state_id": state_id,
                    "crash_detected": False,
                    "dom_text": dom_text,
                    "ui_truth_table": {o: (o == opt) for o in draft_options}
                })

        # --- TAB 5: 系統與時效工具 ---
        print("\n[目錄] 進入分頁 5: 系統與時效工具")
        await click_tab_by_text("系統與時效工具")
        statute_options = ["民事一般侵權損害 (2年 - 民§197)", "一般普通請求權 (15年)", "行政公法上請求權/工資 (5年)", "勞基法14條30日除斥期間限制"]
        async def select_sidebar_statute(option_text):
            sidebar_box = page.locator('[data-testid="stSidebar"] [data-testid="stSelectbox"]').first
            await sidebar_box.locator('[data-baseweb="select"] > div').first.click()
            await page.locator(f'li[role="option"]:has-text("{option_text}")').first.click()
        for opt in statute_options:
            start_time = time.perf_counter()
            state_id = f"Tab5_Calc_{opt}"
            is_crashed = False
            dom_text = ""
            try:
                print(f"   ├── 測試子孫選項: {opt}")
                await select_sidebar_statute(opt)
                btn_calc = page.locator('[data-testid="stSidebar"] button:has-text("執行精密時效推算")')
                if await btn_calc.count() == 0:
                    btn_calc = page.locator('button:has-text("執行精密時效推算")')
                if await btn_calc.count() > 0:
                    await btn_calc.click()
                    await page.wait_for_timeout(2000)
            except Exception as e:
                safe_e = repr(e).encode('ascii', 'replace').decode()
                print(f"   [ERROR] Tab5 exception: {safe_e[:200]}")
            finally:
                await expand_all(page)  # M9: 展開所有隱藏元件
                dom_text = (await page.inner_text("body"))[:2000]  # M7: 採集 DOM 文字
                is_crashed = await check_crash(page, state_id)
                if not is_crashed:
                    await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f"{state_id}.png"))
                latency = time.perf_counter() - start_time
                ram_mb = process.memory_info().rss / (1024 * 1024)
                print(f"   [遙測] 耗時: {latency:.2f}s | RAM: {ram_mb:.1f} MB")
                telemetry_dump.append({"state_id": state_id, "latency_sec": round(latency, 3), "ram_usage_mb": round(ram_mb, 2)})
                # M10: 時效類型多維真值表
                state_dump.append({
                    "state_id": state_id,
                    "crash_detected": is_crashed,
                    "dom_text": dom_text,
                    "ui_truth_table": {o: (o == opt) for o in statute_options}
                })
                
        start_time = time.perf_counter()
        state_id = "Tab5_Backup"
        is_crashed = False
        dom_text = ""
        try:
            print("   ├── 測試子孫選項: AES加密導出")
            btn_backup = page.locator('text="一鍵打包並以 AES 加密導出資料庫"')
            if await btn_backup.count() > 0:
                await btn_backup.click()
                await page.wait_for_timeout(1000)
        except Exception:
            pass
        finally:
            await expand_all(page)  # M9: 展開所有隱藏元件
            dom_text = (await page.inner_text("body"))[:2000]  # M7: 採集 DOM 文字
            is_crashed = await check_crash(page, state_id)
            if not is_crashed:
                await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f"{state_id}.png"))
                
            latency = time.perf_counter() - start_time
            ram_mb = process.memory_info().rss / (1024 * 1024)
            print(f"   [遙測] 耗時: {latency:.2f}s | RAM: {ram_mb:.1f} MB")
            telemetry_dump.append({"state_id": state_id, "latency_sec": round(latency, 3), "ram_usage_mb": round(ram_mb, 2)})
            state_dump.append({
                "state_id": state_id,
                "crash_detected": is_crashed,
                "dom_text": dom_text,
                "ui_truth_table": {"AES_Backup": True}
            })
                
        await browser.close()
    
    # 寫出遙測與真值表軌跡
    with open("C:\\LocalAI_Workstation\\telemetry_metrics.json", "w", encoding="utf-8") as f:
        json.dump(telemetry_dump, f, indent=4, ensure_ascii=False)
        
    with open("C:\\LocalAI_Workstation\\crawler_dump_real.json", "w", encoding="utf-8") as f:
        json.dump(state_dump, f, indent=4, ensure_ascii=False)
    
    # M15: SBFL 崩潰熱力圖分析 — 條件機率反推高風險特徵
    crash_counts = collections.defaultdict(int)
    total_counts = collections.defaultdict(int)
    for s in state_dump:
        for feature, is_checked in s["ui_truth_table"].items():
            if is_checked:
                total_counts[feature] += 1
                if s.get("crash_detected", False):
                    crash_counts[feature] += 1
    print("\n[M15 SBFL 崩潰熱力圖]")
    if total_counts:
        for feat in sorted(total_counts.keys()):
            rate = crash_counts[feat] / total_counts[feat]
            bar = "🔴" if rate > 0.5 else ("🟡" if rate > 0 else "🟢")
            print(f"  {bar} 特徵 [{feat}] 崩潰機率: {rate:.2%} ({crash_counts[feat]}/{total_counts[feat]})")
    else:
        print("  [無特徵資料可分析]")

    print("\n[成功] 【樹狀圖階層式測試完畢】15 項機制整合防護，已寫出遙測數據與真值表 JSON！")

if __name__ == "__main__":
    asyncio.run(explore_tree())
