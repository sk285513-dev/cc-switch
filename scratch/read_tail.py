import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
log_path = r"C:\Users\temp\.gemini\antigravity\brain\77f2801a-1994-462e-a429-6f066a9eb542\.system_generated\tasks\task-851.log"
with open(log_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
    print("".join(lines[-30:]))
