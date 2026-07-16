import json
import os
from pathlib import Path

MANIFESTS = Path('A:/manifests')
for mf in MANIFESTS.glob("task_*.json"):
    os.remove(mf)

print("Cleared manifests")
