import ctypes
import os
import sys
import psutil

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
ATTACH_PARENT_PROCESS = -1

def get_console_text(pid):
    # Free current console just in case
    kernel32.FreeConsole()
    
    # Attach to the target process console
    if not kernel32.AttachConsole(pid):
        return f"Failed to attach to PID {pid}. Error: {ctypes.get_last_error()}"
    
    # Get the handle to the active console screen buffer
    STD_OUTPUT_HANDLE = -11
    hConsole = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
    if hConsole == -1:
        kernel32.FreeConsole()
        return "Failed to get console handle."
    
    # We could read the console output character by character here using ReadConsoleOutputCharacterW
    # For now, let's just prove we can attach
    kernel32.FreeConsole()
    return f"Successfully attached to PID {pid} and verified console."

def scan_powershell_windows():
    print("Scanning for PowerShell windows...")
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'powershell' in proc.info['name'].lower():
                cmdline = " ".join(proc.info['cmdline']) if proc.info['cmdline'] else ""
                if 'kpi_runner' in cmdline or 'workflow.log' in cmdline or 'run_workflow_stderr.log' in cmdline:
                    res = get_console_text(proc.info['pid'])
                    print(f"Found Monitor [PID {proc.info['pid']}]: {cmdline[:50]}... -> {res}")
        except Exception as e:
            pass

if __name__ == '__main__':
    scan_powershell_windows()
