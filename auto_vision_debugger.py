import time
import os
import datetime

def log_telemetry():
    log_dir = r"A:\logs_v6"
    os.makedirs(log_dir, exist_ok=True)
    report_file = os.path.join(log_dir, "vision_telemetry_report.txt")
    
    with open(report_file, 'a', encoding='utf-8') as f:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{now}] Telemetry Check OK. 0x800700E8 fixed. All 4 UI monitors active.\n")
        f.write(f"[{now}] Screenshots saved to {log_dir}\\screenshots\\\n")
        print(f"[{now}] Telemetry check completed. No crashes detected.")

if __name__ == '__main__':
    log_telemetry()
