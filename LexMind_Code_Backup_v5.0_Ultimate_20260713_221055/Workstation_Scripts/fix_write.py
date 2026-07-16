import sys
txt = open('scripts/stt_runner.py', encoding='utf-8').read()
old = '                    tf.write(transcription)\n'
new = '                    tf.write(transcription or "")  # None-safe\n'
if old in txt:
    open('scripts/stt_runner.py', 'w', encoding='utf-8').write(txt.replace(old, new, 1))
    print('OK')
else:
    print('NOT FOUND')
    for i,l in enumerate(txt.split(chr(10))):
        if 'tf.write(transcription' in l:
            print(i+1, repr(l))
