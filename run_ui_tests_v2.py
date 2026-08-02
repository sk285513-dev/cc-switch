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
        
        # In Streamlit, tabs usually have the class 'stTab' or role='tab'
        tabs = page.locator('button[role="tab"]').all()
        print(f"Found {len(tabs)} tabs.")
        
        for i, tab in enumerate(tabs):
            tab_name = tab.get_attribute('id') or f"tab_{i}"
            print(f"Clicking tab {i+1}")
            tab.click(force=True)
            time.sleep(3) # Wait for tab to load and stabilize
            
            # Sub-tabs
            sub_tabs = page.locator('button[role="tab"]').all()
            screenshot_path = f"A:\\logs\\ui_tests\\tab_{i}.png"
            page.screenshot(path=screenshot_path)
            
        browser.close()

if __name__ == '__main__':
    run()
