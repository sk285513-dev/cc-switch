
import traceback
import logging

def log_error(msg):
    print(f'LOG_ERROR: {msg}')

class MockQM:
    def acquire_key_exclusive(self):
        return None
    def release_key(self, k):
        pass

def _run_task_steps(*args):
    return True

from pathlib import Path

manifest = {'task_id': 'mock1'}

def run_single_task_safe(manifest, manifest_path, exclusive_key, qm, chunking_only, stagger=0):
    try:
        paths = {'logs_dir': '.'}
        task_id = manifest['task_id']
        key_acquired_here = False
        stt_engine = 'gemini'
        
        if stt_engine == 'vertexai':
            exclusive_key = 'VERTEX_AI'
        elif not chunking_only and exclusive_key is None and qm is not None:
            try:
                exclusive_key = qm.acquire_key_exclusive()
                key_acquired_here = True
                print(f'DEBUG: exclusive_key={exclusive_key}')
                # THIS WILL CRASH!
                print(f'[Parallel Dispatcher] Task {task_id} 開始，按需取得金鑰: {exclusive_key[:8]}...')
            except RuntimeError:
                return False
        elif exclusive_key:
            print(f'using {exclusive_key[:8]}')
            
        try:
            return _run_task_steps(manifest, manifest_path, paths, exclusive_key, chunking_only)
        except Exception as e:
            return False
        finally:
            if key_acquired_here and qm and exclusive_key:
                qm.release_key(exclusive_key)
    except Exception as e:
        traceback.print_exc()
        log_error(f'[Parallel Dispatcher] Task {task_id} 發生異常：{e}')
        return False

run_single_task_safe(manifest, Path('.'), None, MockQM(), False)
