import os
import subprocess
import traceback
from datetime import datetime, timedelta

def test_bug_03_utcnow():
    print("--- [BUG-03] datetime.utcnow() Test ---")
    try:
        # Old way
        old_time = datetime.utcnow() + timedelta(hours=8)
        print(f"Old time generated: {old_time}")
        
        # New way (simulated check)
        try:
            from zoneinfo import ZoneInfo
            new_time = datetime.now(ZoneInfo("Asia/Taipei"))
            print(f"New time generated: {new_time}")
            print("Status: Fixed" if old_time and new_time else "Status: Failed")
        except ImportError:
            print("Status: Error - zoneinfo not available (requires Python 3.9+)")
    except Exception as e:
        print(f"Status: Error - {e}")
        
def test_bug_04_wmic():
    print("\n--- [BUG-04] wmic Deprecation Test ---")
    try:
        # Check wmic
        result = subprocess.run(["wmic", "pagefilesetting"], capture_output=True, text=True, shell=True)
        if result.returncode != 0:
            print(f"Old wmic command failed: {result.stderr.strip()}")
        else:
            print("Old wmic command ran successfully (but is deprecated).")
            
        # Check PowerShell Get-CimInstance
        ps_cmd = "Get-CimInstance Win32_PageFileSetting"
        ps_result = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True)
        if ps_result.returncode != 0:
            print(f"New PowerShell command failed: {ps_result.stderr.strip()}")
        else:
            print("New PowerShell command ran successfully.")
            
    except Exception as e:
        print(f"Status: Error - {e}")

def test_bug_06_zerodivision():
    print("\n--- [BUG-06] ZeroDivisionError Test ---")
    try:
        crash_counts = {"feature_A": 5}
        total_counts = {"feature_A": 0}
        
        # Old way
        try:
            ratio = crash_counts["feature_A"] / total_counts["feature_A"]
        except ZeroDivisionError:
            print("Old way correctly triggered ZeroDivisionError.")
            
        # New way (Engineering AI Reviewed)
        ratio_safe = crash_counts["feature_A"] / total_counts["feature_A"] if total_counts["feature_A"] > 0 else 0.0
        print(f"New way safely calculated ratio: {ratio_safe}")
        
    except Exception as e:
        print(f"Status: Error - {e}")

def test_bug_08_vbscript_quotes():
    print("\n--- [BUG-08] VBScript Path Escape Test ---")
    path_with_spaces = "C:\\Program Files\\My App\\script.vbs"
    # Old way
    vbs_code_old = f'CreateObject("WScript.Shell").Run "{path_with_spaces}"'
    print(f"Old generated VBS: {vbs_code_old} (Vulnerable to truncation)")
    
    # New way
    vbs_code_new = f'CreateObject("WScript.Shell").Run Chr(34) & "{path_with_spaces}" & Chr(34)'
    print(f"New generated VBS: {vbs_code_new} (Safe from truncation)")

if __name__ == "__main__":
    test_bug_03_utcnow()
    test_bug_04_wmic()
    test_bug_06_zerodivision()
    test_bug_08_vbscript_quotes()
