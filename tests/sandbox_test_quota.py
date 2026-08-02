import threading
import time
import sys
import random
from concurrent.futures import ThreadPoolExecutor

sys.path.append("C:/LocalAI_Workstation/scripts")
from quota_manager import QuotaManager

# Mocking time.sleep to run faster in tests
real_sleep = time.sleep
def mock_sleep(secs):
    real_sleep(secs * 0.1) # 10x faster for testing
time.sleep = mock_sleep

qm = QuotaManager()
# reset pool for test
with qm._lock:
    qm.keys = [f"TEST_KEY_{i}" for i in range(5)]
    qm.key_status = {k: {"exhausted": False, "retry_count": 0, "last_failed": None} for k in qm.keys}


log_lock = threading.Lock()
def tlog(msg):
    with log_lock:
        print(f"[{threading.current_thread().name}] {msg}")

def simulate_agent_task(agent_id):
    key = None
    try:
        tlog(f"Agent {agent_id} starting...")
        key = qm.acquire_key_exclusive()
        tlog(f"Agent {agent_id} acquired key {key}")
        consecutive_429 = 0
        for i in range(3):
            # Simulate work
            real_sleep(0.1)
            # Simulate random 429
            if random.random() < 0.7:
                err = Exception("429 Too Many Requests")
                consecutive_429 += 1
                tlog(f"Agent {agent_id} hit 429 on key {key}, consecutive {consecutive_429}")
                res = qm.handle_error(err, key, consecutive_429)
                tlog(f"Agent {agent_id} handle_error => sleep {res['sleep_time']:.1f}s, new_key: {res['new_key']}")
                if res["sleep_time"] > 0:
                    time.sleep(res["sleep_time"])
                if res["new_key"]:
                    # Wait, if we acquired exclusively, handle_error might give us a new key.
                    qm.release_key(key)
                    key = res["new_key"]
                    consecutive_429 = 0
                    # For safety in test, we should lock the new key, but handle_error just returns a round-robin key, which might not be exclusively locked! 
                    # If handle_error is used in exclusive mode, the script should actually call acquire_key_exclusive() instead of using res["new_key"] directly, because res["new_key"] is just for round-robin.
                    # Wait, QuotaManager.handle_error does this:
                    # if consecutive_429 >= 3: mark exhausted, return new_key = self.acquire_key()
                    # It calls acquire_key() which is round-robin (shared lock)!
                    # This means if an exclusive task calls handle_error and gets a new key, it's NOT exclusively locked.
                    tlog(f"Agent {agent_id} rotated to key {key}")
        tlog(f"Agent {agent_id} finished successfully with key {key}.")
    except Exception as e:
        tlog(f"Agent {agent_id} failed: {e}")
    finally:
        if key:
            qm.release_key(key)
            tlog(f"Agent {agent_id} released key {key}")

def run_test():
    with ThreadPoolExecutor(max_workers=10) as exec:
        futures = [exec.submit(simulate_agent_task, i) for i in range(20)]
        for f in futures:
            f.result()
    tlog("All agents completed.")

if __name__ == "__main__":
    run_test()
