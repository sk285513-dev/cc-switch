import subprocess
result = subprocess.run(
    ["powershell", "-Command",
     "Get-WmiObject Win32_Process -Filter \"Name='python.exe'\" | "
     "Where-Object { $_.CommandLine -match 'run_workflow' } | "
     "Select-Object -First 1 -ExpandProperty ProcessId"],
    capture_output=True, text=True, timeout=10
)
print("OUT:", repr(result.stdout))
print("ERR:", repr(result.stderr))
