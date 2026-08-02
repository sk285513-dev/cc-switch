import subprocess
try:
    result = subprocess.check_output('wmic process where "name like \'%python%\'" get commandline,processid', shell=True).decode('utf-8', errors='replace')
    print(result)
except Exception as e:
    print(e)
