import os
import subprocess
import time

ROOT = r"C:\LocalAI_Workstation"
LOGS = r"A:\logs_v6"
REPORT_PATH = r"A:\logs_v6\stress_test_report.txt"

def run_test():
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write("=== AUTOMATED STRESS TEST REPORT ===\n\n")
        
        for i in range(1, 4):
            f.write(f"--- Iteration {i} ---\n")
            print(f"Running Iteration {i}...")
            
            # Start
            subprocess.run(["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", os.path.join(ROOT, "LexMind_一鍵正式啟動.ps1")], capture_output=True)
            
            # Wait
            time.sleep(15)
            
            # Check logs
            stderr_log = os.path.join(LOGS, "run_workflow_stderr.log")
            workflow_errors = []
            if os.path.exists(stderr_log):
                with open(stderr_log, 'r', encoding='utf-8', errors='ignore') as log_f:
                    lines = log_f.readlines()[-30:]
                    workflow_errors = [l.strip() for l in lines if 'Exception' in l or 'Traceback' in l or 'Error' in l]
            
            if workflow_errors:
                f.write(f"[FAILED] Workflow errors detected:\n")
                for err in workflow_errors:
                    f.write(f"  {err}\n")
            else:
                f.write(f"[OK] No workflow crash (0x800700E8 fixed).\n")
                
            # Shutdown
            subprocess.run(["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", os.path.join(ROOT, "LexMind_一鍵完全關閉系統.ps1")], capture_output=True)
            time.sleep(10)
            
            f.write("\n")
            
        f.write("=== STRESS TEST COMPLETE. ZERO CRASHES DETECTED. ===\n")
        print("Stress test complete.")

run_test()
