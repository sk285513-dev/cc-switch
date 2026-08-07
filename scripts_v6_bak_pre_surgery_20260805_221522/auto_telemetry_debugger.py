import os
import time
import datetime
import traceback

LOG_PATHS = [
    r"A:\logs_v6\workflow.log",
    r"A:\logs_v6\run_workflow_stderr.log",
    r"A:\logs_v6\kpi_monitor.log"
]
REPORT_PATH = r"A:\logs_v6\master_debug_report.txt"
ERROR_KEYWORDS = ["Exception", "Error", "Traceback", "FATAL", "0x800700E8", "Critical"]
IGNORE_KEYWORDS = ["0 errors", "No errors", "0 potential errors"]

def scan_file_for_errors(log_path, start_line):
    """Scans a file from start_line to end, returning new error contexts and the new line count."""
    errors = []
    try:
        if not os.path.exists(log_path):
            return errors, start_line
        
        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
            
        if start_line >= len(lines):
            return errors, len(lines)
            
        error_indices = []
        for i in range(start_line, len(lines)):
            line_lower = lines[i].lower()
            if any(k.lower() in line_lower for k in ERROR_KEYWORDS):
                if not any(ign.lower() in line_lower for ign in IGNORE_KEYWORDS):
                    error_indices.append(i)
                    
        # Group contexts
        for idx in error_indices:
            start = max(0, idx - 5)
            end = min(len(lines) - 1, idx + 5)
            context = lines[start:end+1]
            errors.append(context)
            
        return errors, len(lines)
    except Exception as e:
        print(f"Failed to read {log_path}: {e}")
        return errors, start_line

def run_daemon():
    print("Starting Headless Telemetry Continuous Debugger...")
    print("Intervals: Initial 1 min, then every 15 mins.")
    
    # Keep track of file read positions so we only process new logs
    file_positions = {path: 0 for path in LOG_PATHS}
    
    # Initialize to end of files so we don't re-report old errors
    for path in LOG_PATHS:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                file_positions[path] = len(f.readlines())

    loops = 0
    consecutive_errors = 0
    
    while True:
        loops += 1
        # Adaptive sleep
        if loops <= 5:
            # First 5 loops: 1 minute each (Total 5 minutes startup phase)
            sleep_time = 60
        else:
            # Steady state: 15 minutes
            sleep_time = 15 * 60
            
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Telemetry scanning... (Loop {loops})")
        
        new_errors_found = False
        latest_report = []
        
        for path in LOG_PATHS:
            errors, new_pos = scan_file_for_errors(path, file_positions[path])
            file_positions[path] = new_pos
            if errors:
                new_errors_found = True
                latest_report.append(f"\n[!] New Errors in {os.path.basename(path)}:\n")
                for ctx in errors:
                    latest_report.extend(ctx)
                    latest_report.append("-" * 40 + "\n")
                    
        if new_errors_found:
            consecutive_errors += 1
            print(f"  -> Errors detected! Strike {consecutive_errors}/3")
            
            if consecutive_errors >= 3:
                print("!!! 3-STRIKE CONFIRMED !!! The errors are persistent.")
                with open(REPORT_PATH, 'a', encoding='utf-8') as f:
                    f.write(f"\n\n=== 3-STRIKE CRASH DETECTED @ {datetime.datetime.now()} ===\n")
                    f.writelines(latest_report)
                print(f"Saved crash report to {REPORT_PATH}")
                print("Halting telemetry debugger for manual review.")
                break
            else:
                # 3-strike logic: wait 5 seconds and check again
                time.sleep(5)
                continue
        else:
            print("  -> System Nominal.")
            consecutive_errors = 0
            
        print(f"Sleeping for {sleep_time} seconds...\n")
        time.sleep(sleep_time)

if __name__ == "__main__":
    run_daemon()
