import threading
import time
import random
import logging
from pathlib import Path
from key_manager import KeyManager
from quota_manager import QuotaManager
from google.api_core import exceptions as google_exceptions

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class MockGeminiClient:
    def __init__(self, key):
        self.key = key

    def generate_content(self, *args, **kwargs):
        # 模擬呼叫延遲
        time.sleep(random.uniform(0.1, 0.5))
        # 隨機觸發 429 或 503
        r = random.random()
        if r < 0.3:
            raise google_exceptions.ResourceExhausted("Mock 429 Too Many Requests")
        elif r < 0.4:
            raise google_exceptions.ServiceUnavailable("Mock 503 Server Error")
        return "Mock transcription success"

def mock_worker(worker_id, qm):
    consecutive_429_count = 0
    current_key = qm.acquire_key()
    logging.info(f"Worker {worker_id} started with key {current_key[:8]}")

    for i in range(5):
        client = MockGeminiClient(current_key)
        try:
            client.generate_content()
            logging.info(f"Worker {worker_id} success on iter {i}")
            consecutive_429_count = 0
        except Exception as e:
            logging.warning(f"Worker {worker_id} error on iter {i}: {e}")
            if isinstance(e, (google_exceptions.ResourceExhausted, google_exceptions.TooManyRequests)):
                consecutive_429_count += 1
                res = qm.handle_error(e, current_key, consecutive_429_count)
                new_key = res["new_key"]
                if new_key and new_key != current_key:
                    logging.info(f"Worker {worker_id} switching key to {new_key[:8]}")
                    current_key = new_key
                    consecutive_429_count = 0
                if res["sleep_time"] > 0:
                    time.sleep(min(res["sleep_time"], 1)) # cap sleep time for testing
            else:
                pass

def key_injector(qm):
    for i in range(3):
        time.sleep(2)
        new_key = f"TEST_INJECTED_KEY_{random.randint(1000,9999)}"
        logging.info(f"Injecting new key: {new_key}")
        KeyManager.add_keys_from_cli(new_key)
        # QuotaManager 重新載入 key
        qm._load_keys()

def run_test():
    qm = QuotaManager(keys_path="config/keys.yaml", policy_path="config/quota_policy.yaml", state_path="config/quota_state.json")
    
    threads = []
    
    # 啟動 10 個 worker
    for i in range(10):
        t = threading.Thread(target=mock_worker, args=(i, qm))
        threads.append(t)
        t.start()
        
    # 啟動 injector
    injector_t = threading.Thread(target=key_injector, args=(qm,))
    injector_t.start()
    
    for t in threads:
        t.join()
        
    injector_t.join()
    logging.info("Test finished successfully. No deadlocks detected.")

if __name__ == "__main__":
    run_test()
