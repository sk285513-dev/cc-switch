import sys
import subprocess
import os

if len(sys.argv) > 1:
    args = sys.argv[1:]
    cmd_list = []
    for arg in args:
        if ' ' in arg or ';' in arg or '=' in arg or '{' in arg or '&' in arg:
            cmd_list.append(f'"{arg}"')
        else:
            cmd_list.append(arg)
    
    cmd_str = " ".join(cmd_list)
    CREATE_NEW_CONSOLE = 0x00000010
    DETACHED_PROCESS = 0x00000008
    # Use CREATE_NEW_CONSOLE so it gets a visible window
    subprocess.Popen(cmd_str, creationflags=CREATE_NEW_CONSOLE, close_fds=True, shell=False)
