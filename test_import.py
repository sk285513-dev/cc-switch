import os
import sys
sys.path.insert(0, r'C:\LocalAI_Workstation\scripts_v6')
try:
    import run_workflow
    print(dir(run_workflow))
except Exception as e:
    import traceback
    traceback.print_exc()
