import multiprocessing, time, sys

def f():
    print(\ child start\, flush=True)
    time.sleep(3)
    print(\child end\, flush=True)

if __name__ == \__main__\:
    print(\parent start\, flush=True)
    p = multiprocessing.Process(target=f)
    p.daemon = True
    p.start()
    print(\parent end, waiting 1s\, flush=True)
    time.sleep(1)
    print(\parent exit\, flush=True)
