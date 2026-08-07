import os
import hashlib
import logging

logger = logging.getLogger(__name__)

def get_file_hash(f_path: str) -> str | None:
    """
    Computes a sparse SHA-256 hash for a file.
    Includes the file size in the hash computation.
    - If size < 3MB, hashes the entire file.
    - If size >= 3MB, hashes the first 1MB, middle 1MB, and last 1MB.
    """
    MB = 1024 * 1024
    
    try:
        if not os.path.isfile(f_path):
            raise FileNotFoundError(f"File not found: {f_path}")
            
        file_size = os.path.getsize(f_path)
        hasher = hashlib.sha256()
        
        # Include file size in the hash
        hasher.update(f"SIZE:{file_size}".encode('utf-8'))
        
        with open(f_path, 'rb') as f:
            if file_size < 3 * MB:
                # Hash the whole file
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    hasher.update(chunk)
            else:
                # Sparse hashing
                # First 1MB
                hasher.update(f.read(MB))
                
                # Middle 1MB
                mid_offset = (file_size // 2) - (MB // 2)
                f.seek(mid_offset)
                hasher.update(f.read(MB))
                
                # Last 1MB
                end_offset = file_size - MB
                f.seek(end_offset)
                hasher.update(f.read(MB))
                
        return hasher.hexdigest()
    
    except Exception as e:
        logger.error(f"Error computing hash for {f_path}: {str(e)}", exc_info=True)
        return None
