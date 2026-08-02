import os

file_path = r'C:\LocalAI_Workstation\scripts_v6\stt_runner.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('MANIFEST_QUEUE = queue.Queue()', '')
content = content.replace('def ManifestWriterThread(chunks_manifest_path):', 'def ManifestWriterThread(chunks_manifest_path, manifest_queue):')
content = content.replace('MANIFEST_QUEUE', 'manifest_queue')

content = content.replace('DISTILL_QUEUE = queue.Queue()', '')
content = content.replace('def DistillWorkerThread(worker_id):', 'def DistillWorkerThread(worker_id, distill_queue):')
content = content.replace('DISTILL_QUEUE', 'distill_queue')

content = content.replace(
    'def process_single_chunk(\n    chunk: dict, client, qm: QuotaManager, current_key_ref: list, key_lock: threading.Lock,\n    task_id: str, chunks_manifest_path: str, config: dict, chunk_errors_log: str, stt_engine: str\n) -> bool:',
    'def process_single_chunk(\n    chunk: dict, client, qm: QuotaManager, current_key_ref: list, key_lock: threading.Lock,\n    task_id: str, chunks_manifest_path: str, config: dict, chunk_errors_log: str, stt_engine: str, manifest_queue: queue.Queue, distill_queue: queue.Queue\n) -> bool:'
)

run_stt_old = '''    writer_thread = threading.Thread(target=ManifestWriterThread, args=(chunks_manifest_path,), daemon=False)
    writer_thread.start()

    # 啟動背景蒸餾工作池 (12 Workers)
    distill_workers = []
    for i in range(12):
        t = threading.Thread(target=DistillWorkerThread, args=(i,), daemon=False)
        t.start()
        distill_workers.append(t)'''

run_stt_new = '''    manifest_queue = queue.Queue()
    distill_queue = queue.Queue()

    writer_thread = threading.Thread(target=ManifestWriterThread, args=(chunks_manifest_path, manifest_queue), daemon=False)
    writer_thread.start()

    # 啟動背景蒸餾工作池 (12 Workers)
    distill_workers = []
    for i in range(12):
        t = threading.Thread(target=DistillWorkerThread, args=(i, distill_queue), daemon=False)
        t.start()
        distill_workers.append(t)'''

content = content.replace(run_stt_old, run_stt_new)

submit_old = '''executor.submit(process_single_chunk, chunk, client, qm, current_key_ref, key_lock, task_id, chunks_manifest_path, config, chunk_errors_log, stt_engine): chunk'''
submit_new = '''executor.submit(process_single_chunk, chunk, client, qm, current_key_ref, key_lock, task_id, chunks_manifest_path, config, chunk_errors_log, stt_engine, manifest_queue, distill_queue): chunk'''
content = content.replace(submit_old, submit_new)

join_old = '''    manifest_queue.put("STOP")
    for _ in range(12):
        distill_queue.put("STOP")
        
    manifest_queue.join()
    distill_queue.join()'''

join_new = '''    manifest_queue.put("STOP")
    for _ in range(12):
        distill_queue.put("STOP")
        
    writer_thread.join()
    for t in distill_workers:
        t.join()'''

content = content.replace(join_old, join_new)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Done')
