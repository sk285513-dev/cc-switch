import subprocess
try:
    subprocess.Popen('cmd.exe /c start powershell.exe -NoProfile -NoExit -Command "Write-Host Hello"', shell=False)
    print("Launched via cmd start successfully.")
except Exception as e:
    print("Error:", e)
