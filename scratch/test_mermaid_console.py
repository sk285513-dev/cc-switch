import time
from playwright.sync_api import sync_playwright

code = '''graph TD
    subgraph DataProducers ["寫入端 (Data Producers)"]
        G1["Group 1 - 物流與規則<br>auto_ingest_bot"] -->|寫入進度| JSON1("ingest_state.json")
        G1 -->|寫入佇列| JSON2("batch_progress.json")
        G2["Group 2 - 加工管線<br>run_workflow"] -->|寫入任務狀態| LOG("workflow.log")
        G6["Group 6 - 外部爬蟲<br>law_scraper_cli"] -->|寫入題庫| JSON3("crawler_dump_real.json")
    end
'''

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.on("console", lambda msg: print(f"Browser Console: {msg.text}"))
    page.on("pageerror", lambda err: print(f"Page Error: {err.message}"))
    
    html = f'''<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>
        document.addEventListener("DOMContentLoaded", function() {{
            try {{
                mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
            }} catch (e) {{
                console.error("Init error:", e);
            }}
        }});
    </script>
</head>
<body>
    <div class="mermaid">{code}</div>
</body>
</html>'''
    
    temp_html = "C:/Users/temp/Downloads/test_console.html"
    with open(temp_html, 'w', encoding='utf-8') as f:
        f.write(html)
        
    page.goto(f"file:///{temp_html}")
    try:
        page.wait_for_selector('svg', timeout=5000)
        print("Success!")
    except Exception as e:
        print("Timeout.")
    browser.close()
