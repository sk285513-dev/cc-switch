import sys
import logging
from pathlib import Path
sys.path.append(r"C:\LocalAI_Workstation\scripts_v6")

logging.basicConfig(
    filename=r"A:\logs\workflow.log",
    level=logging.WARNING,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

from llm_gateway import call_llm_with_resilience
import threading

def run_call():
    res = call_llm_with_resilience(
        stage="map",
        task_id="test_task_dup_123",
        chunk_id="part_999",
        prompt="hello",
        model_name="gemini-2.5-flash",
        api_key="dummy",
        qm=None,
        timeout=10.0
    )
    if res.error_code == "DUPLICATE_INFLIGHT":
        print(f"DUPLICATE_INFLIGHT detected: {res.error_message}")

t1 = threading.Thread(target=run_call)
t2 = threading.Thread(target=run_call)
t1.start()
t2.start()
t1.join()
t2.join()
