import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.quota_manager import QuotaManager

try:
    qm = QuotaManager()
    print(f"SUCCESS: Loaded {len(qm.keys)} API keys.")
    print("Keys preview:")
    for k in qm.keys:
        print(f"  - {k[:8]}...{k[-4:]}")
except Exception as e:
    print(f"FAILED to initialize QuotaManager: {e}")
