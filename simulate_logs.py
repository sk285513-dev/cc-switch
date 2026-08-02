import time
import os

LOG_FILE = r"A:\logs\workflow.log"

def simulate_bom_error():
    print("Writing fake BOM error...")
    with open(LOG_FILE, 'a', encoding='utf-8-sig') as f:
        f.write("[2026-07-18 22:22:52] [ERROR] Workflow Engine: Critical error in task mock_123: Unexpected UTF-8 BOM (decode using utf-8-sig): line 1 column 1 (char 0)\n")

def simulate_thundering_herd():
    print("Writing 35 fake [Key Pool] messages in 1 second...")
    with open(LOG_FILE, 'a', encoding='utf-8-sig') as f:
        for i in range(35):
            f.write(f"[2026-07-18 22:22:52] [INFO] [Key Pool] 成功標記 API Key MOCK_KEY_{i} 為「暫時耗盡」。\n")
    print("Done writing.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "bom":
        simulate_bom_error()
    elif len(sys.argv) > 1 and sys.argv[1] == "herd":
        simulate_thundering_herd()
    else:
        print("Usage: python simulate_logs.py [bom|herd]")
