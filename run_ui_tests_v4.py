from playwright.sync_api import sync_playwright
import time
import os

def run():
    os.makedirs('A:\\logs\\ui_tests', exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto('http://localhost:8501')
        print("Waiting for app to load...")
        page.wait_for_selector('div.stApp', timeout=15000)
        time.sleep(5)
        
        tab_texts = [
            "💬 實務辯護諮詢", 
            "📥 知識餵養", 
            "📂 法律人口管理", 
            "🔍 教材搜尋與定位", 
            "🎓 司法官自我養成", 
            "📝 訴訟書狀草案", 
            "⚙️系統與時效工具", 
            "🤖 Antigravity 控制台"
        ]
        
        for i, text in enumerate(tab_texts):
            try:
                # Find the tab by partial text match
                tab = page.locator(f"text='{text}'").first
                if tab.count() > 0:
                    print(f"Clicking tab {i+1}: {text}")
                    tab.click(force=True)
                    time.sleep(3) # Wait for render
                    screenshot_path = f"A:\\logs\\ui_tests\\tab_{i}.png"
                    page.screenshot(path=screenshot_path)
                    print(f"Saved {screenshot_path}")
                else:
                    print(f"Tab '{text}' not found.")
            except Exception as e:
                print(f"Error on tab '{text}': {e}")
            
        browser.close()

if __name__ == '__main__':
    run()
