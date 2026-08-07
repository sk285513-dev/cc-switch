import os
import time
import datetime
import win32gui
import win32ui
import win32con
from PIL import Image
import pytesseract

# Ensure Tesseract path is set correctly
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

REPORT_PATH = r"A:\logs\master_debug_report.txt"
ARTIFACTS_DIR = r"A:\logs\screenshots"

if not os.path.exists(ARTIFACTS_DIR):
    os.makedirs(ARTIFACTS_DIR)

def get_window_image_and_text(hwnd):
    """Captures the window image and returns OCR text."""
    try:
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top
        if width <= 0 or height <= 0:
            return None, ""

        hwindc = win32gui.GetWindowDC(hwnd)
        srcdc = win32ui.CreateDCFromHandle(hwindc)
        memdc = srcdc.CreateCompatibleDC()
        bmp = win32ui.CreateBitmap()
        bmp.CreateCompatibleBitmap(srcdc, width, height)
        memdc.SelectObject(bmp)
        
        # PW_CLIENTONLY might be needed, but default 0 captures whole window
        result = win32gui.PrintWindow(hwnd, memdc.GetSafeHdc(), 0)
        
        if result == 1:
            bmpinfo = bmp.GetInfo()
            bmpstr = bmp.GetBitmapBits(True)
            img = Image.frombuffer(
                'RGB',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRX', 0, 1
            )
            # Perform OCR
            text = pytesseract.image_to_string(img, lang='eng+chi_tra')
            
            # Save temporary image for strike history if needed
            temp_path = os.path.join(ARTIFACTS_DIR, f"temp_{hwnd}.png")
            img.save(temp_path)
            
            # Cleanup
            win32gui.DeleteObject(bmp.GetHandle())
            memdc.DeleteDC()
            srcdc.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwindc)
            
            return temp_path, text
        else:
            win32gui.DeleteObject(bmp.GetHandle())
            memdc.DeleteDC()
            srcdc.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwindc)
            return None, ""
    except Exception as e:
        print(f"Failed to capture hwnd {hwnd}: {e}")
        return None, ""

def find_target_windows():
    """Finds all visible PowerShell or CMD windows related to our system."""
    targets = []
    def callback(hwnd, extra):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if "PowerShell" in title or "Windows PowerShell" in title or "cmd.exe" in title.lower():
                targets.append((hwnd, title))
    win32gui.EnumWindows(callback, None)
    return targets

def check_baseline(text):
    """
    Checks if the OCR text contains expected normal behavior.
    Returns (is_normal, error_reason)
    """
    text_lower = text.lower()
    
    # 1. Explicit Error Keywords
    error_keywords = ["error", "exception", "traceback", "0x800700e8", "fatal"]
    for err in error_keywords:
        if err in text_lower:
            return False, f"Detected error keyword: {err}"
            
    # 2. Baseline Features (Must have at least one indicator of life if it's our script)
    # We look for common logs: [INFO], KPI, Dashboard, Progress, etc.
    baseline_keywords = ["info", "kpi", "dashboard", "progress", "stage", "chunk", "dispatch", "啟動", "正常", "202"] # 202 for year 2026/2025 timestamps
    
    has_baseline = any(b in text_lower for b in baseline_keywords)
    
    # Empty screen might be stderr waiting for errors, which is normal for stderr but not others.
    # To be safe, if it's completely empty, we'll let it pass unless it stays empty and another window crashes.
    if len(text.strip()) < 5:
        return True, "Empty console (Waiting)"
        
    if not has_baseline:
        # Not empty, no error keywords, but no baseline features. Might be frozen or displaying garbage.
        return False, "Failed baseline feature check (No INFO/KPI/Date found)"
        
    return True, "Normal"

def run_daemon():
    print("Starting Vision OCR Continuous Debugger...")
    print("Intervals: Initial 1 min, then every 15 mins.")
    
    loops = 0
    consecutive_errors = 0
    
    while True:
        loops += 1
        if loops <= 5:
            sleep_time = 60
        else:
            sleep_time = 15 * 60
            
        print(f"\n[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Vision OCR scanning... (Loop {loops})")
        
        targets = find_target_windows()
        if not targets:
            print("  -> No PowerShell windows found.")
            time.sleep(sleep_time)
            continue
            
        any_error = False
        latest_report = []
        
        for hwnd, title in targets:
            img_path, ocr_text = get_window_image_and_text(hwnd)
            if ocr_text:
                is_normal, reason = check_baseline(ocr_text)
                if not is_normal:
                    any_error = True
                    latest_report.append(f"Window: {title} (HWND {hwnd})\nReason: {reason}\nOCR Text:\n{ocr_text}\nImage saved to: {img_path}\n")
        
        if any_error:
            consecutive_errors += 1
            print(f"  -> Abnormal visual state detected! Strike {consecutive_errors}/3")
            
            if consecutive_errors >= 3:
                print("!!! 3-STRIKE CONFIRMED !!! Visual crash or freeze persistent.")
                with open(REPORT_PATH, 'a', encoding='utf-8') as f:
                    f.write(f"\n\n=== 3-STRIKE VISUAL CRASH DETECTED @ {datetime.datetime.now()} ===\n")
                    f.writelines(latest_report)
                print(f"Saved crash report to {REPORT_PATH}")
                print("Halting vision debugger for manual review.")
                break
            else:
                # 3-strike logic: wait 5 seconds and check again
                time.sleep(5)
                continue
        else:
            print("  -> Visual State Nominal. Baseline features present.")
            consecutive_errors = 0
            
        print(f"Sleeping for {sleep_time} seconds...")
        time.sleep(sleep_time)

if __name__ == "__main__":
    run_daemon()

