from playwright.sync_api import sync_playwright
import time
import re

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto('http://localhost:8501')
        print("Waiting for app to load...")
        page.wait_for_selector('div.stApp', timeout=15000)
        time.sleep(5)
        
        html = page.content()
        # Find tab buttons by looking for their text
        tab_texts = ["💬 實務辯護諮詢", "📥 知識餵養 (影音 & 書狀)"]
        for t in tab_texts:
            if t in html:
                print(f"Found '{t}' in HTML.")
            else:
                print(f"Did NOT find '{t}' in HTML.")
        
        # Save html snippet
        with open('A:\\logs\\streamlit_html.txt', 'w', encoding='utf-8') as f:
            f.write(html)
            
        browser.close()

if __name__ == '__main__':
    run()
