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
        
        # Use playwright's built-in role selector for ARIA tab role
        tabs = page.get_by_role('tab').all()
        print(f"Found {len(tabs)} tabs.")
        
        # We will only click the first 8 main tabs to avoid an infinite loop of sub-tabs
        for i, tab in enumerate(tabs[:8]):
            print(f"Clicking tab {i+1}")
            try:
                tab.click(force=True)
                time.sleep(3) # Wait for tab to load and stabilize
                screenshot_path = f"A:\\logs\\ui_tests\\tab_{i}.png"
                page.screenshot(path=screenshot_path)
                print(f"Saved {screenshot_path}")
            except Exception as e:
                print(f"Failed to click tab {i+1}: {e}")
            
        browser.close()

if __name__ == '__main__':
    run()
