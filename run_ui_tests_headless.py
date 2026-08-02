import os
import sys
from playwright.sync_api import sync_playwright, expect

def run_ui_tests():
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    
    output_dir = r"A:\logs\ui_tests"
    os.makedirs(output_dir, exist_ok=True)
    
    print("啟動測試...")

    tab_names = [
        "💬 實務辯護諮詢", 
        "📥 知識餵養 (影音 & 書狀)", 
        "📂 法律人口管理", 
        "🔍 教材搜尋與定位", 
        "🎓 司法官自我養成", 
        "📝 訴訟書狀草案", 
        "⚙️系統與時效工具", 
        "🤖 Antigravity 控制台"
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            page.goto('http://localhost:8501', timeout=30000)
            
            app_container = page.locator('div.stApp')
            expect(app_container).to_be_visible(timeout=15000)
            
            page.screenshot(path=os.path.join(output_dir, "00_首頁快照.png"), full_page=True)
            
            for i, tab_name in enumerate(tab_names):
                try:
                    tab = page.get_by_role("tab", name=tab_name, exact=True)
                    expect(tab).to_be_visible(timeout=10000)
                    tab.click()
                    
                    spinner = page.locator('[data-testid="stStatusWidget"]')
                    expect(spinner).to_be_hidden(timeout=10000)
                    
                    safe_name = "".join(c for c in tab_name if c.isalnum() or c in (' ', '_'))[:15]
                    screenshot_path = os.path.join(output_dir, f"Tab_{i+1}_{safe_name}.png")
                    page.screenshot(path=screenshot_path)
                    print(f"✅ {screenshot_path}")
                    
                except Exception as e:
                    print(f"❌ 標籤頁 '{tab_name}' 測試失敗: {e}")

        except Exception as e:
            print(f"💥 測試過程發生致命錯誤: {e}")
        finally:
            context.close()
            browser.close()

if __name__ == '__main__':
    run_ui_tests()
