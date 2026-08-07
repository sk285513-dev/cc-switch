import base64
import zlib
import urllib.request

code = '''graph TD
    subgraph 寫入端 (Data Producers)
        G1["Group 1 - 物流與規則<br>auto_ingest_bot"] -->|寫入進度| JSON1(ingest_state.json)
        G1 -->|寫入佇列| JSON2(batch_progress.json)
        G2["Group 2 - 加工管線<br>run_workflow"] -->|寫入任務狀態| LOG(workflow.log)
        G6["Group 6 - 外部爬蟲<br>law_scraper_cli"] -->|寫入題庫| JSON3(crawler_dump_real.json)
    end
'''

data = code.encode('utf-8')
compressed = zlib.compress(data, 9)
b64_code = base64.urlsafe_b64encode(compressed).decode('utf-8')
url = f"https://kroki.io/mermaid/png/{b64_code}"

try:
    print(url)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        print("Success Kroki PNG")
except Exception as e:
    print("Error Kroki:", e)
