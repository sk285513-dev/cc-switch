
import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
    open('test_pythonw3.log', 'w').write('SUCCESS')
except Exception as e:
    open('test_pythonw3.log', 'w').write(str(e))

