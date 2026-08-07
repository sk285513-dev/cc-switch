import os
import time
from sparse_hash_coder import get_file_hash

import subprocess

def create_mock_file(path, size_bytes):
    if os.path.exists(path):
        os.remove(path)
    subprocess.run(["fsutil", "file", "createnew", path, "0"], check=True, capture_output=True)
    subprocess.run(["fsutil", "sparse", "setflag", path], check=True, capture_output=True)
    subprocess.run(["fsutil", "file", "seteof", path, str(size_bytes)], check=True, capture_output=True)

def test_hashing():
    small_file = "test_1MB.bin"
    large_file = "test_5GB.bin"
    
    MB = 1024 * 1024
    GB = 1024 * MB
    
    print("Creating mock files...")
    create_mock_file(small_file, 1 * MB)
    create_mock_file(large_file, 5 * GB)
    
    print("Testing small file (1MB)...")
    start = time.time()
    h1 = get_file_hash(small_file)
    elapsed = time.time() - start
    print(f"Small file hash: {h1}, Time: {elapsed:.4f}s")
    
    print("Testing large file (5GB)...")
    start = time.time()
    h2 = get_file_hash(large_file)
    elapsed = time.time() - start
    print(f"Large file hash: {h2}, Time: {elapsed:.4f}s")
    
    # Cleanup
    os.remove(small_file)
    os.remove(large_file)

if __name__ == '__main__':
    test_hashing()
