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
        
        # Streamlit tabs usually have data-baseweb="tab"
        tabs = page.locator('button[data-baseweb="tab"]').all()
        print(f"Found {len(tabs)} tabs.")
        
        for i, tab in enumerate(tabs):
            tab_name = tab.inner_text().strip().replace('\n', ' ')
            print(f"Clicking tab {i+1}: {tab_name}")
            tab.click()
            time.sleep(3) # Wait for tab to load and stabilize
            screenshot_path = f"A:\\logs\\ui_tests\\tab_{i}.png"
            page.screenshot(path=screenshot_path)
            print(f"Saved {screenshot_path}")
            
        browser.close()

if __name__ == '__main__':
    run()
