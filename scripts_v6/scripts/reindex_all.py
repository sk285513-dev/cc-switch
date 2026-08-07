#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LexMind-Omni Master Re-indexing Script
======================================
1. Runs Obsidian → RAGFlow Sync
2. Runs Codebase Graph Memory Indexer
"""

import os
import sys
import subprocess
import json

def main():
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    print("=== [1/2] Syncing Obsidian Vault to RAGFlow ===")
    sync_script = os.path.join(script_dir, "obsidian_ragflow_sync.py")
    sync_res = subprocess.run([sys.executable, sync_script], capture_output=False)
    if sync_res.returncode != 0:
        print("⚠️ Obsidian sync warning or non-zero code returned, continuing to index codebase graph...")

    print("\n=== [2/2] Re-indexing Codebase Graph Memory ===")
    mcp_exe = os.path.expandvars(r"%LOCALAPPDATA%\Programs\codebase-memory-mcp\codebase-memory-mcp.exe")
    if not os.path.exists(mcp_exe):
        # Fallback to temp path if localappdata doesn't resolve correctly
        mcp_exe = r"C:\Users\temp\AppData\Local\Programs\codebase-memory-mcp\codebase-memory-mcp.exe"
        
    if os.path.exists(mcp_exe):
        args = {"repo_path": project_root.replace("\\", "/")}
        cmd = [mcp_exe, "cli", "index_repository", json.dumps(args)]
        print(f"Running: {' '.join(cmd)}")
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if res.returncode == 0:
            print("✅ Codebase indexed successfully!")
            print(res.stdout)
        else:
            print("❌ Codebase indexing failed!")
            print("STDERR:", res.stderr)
            print("STDOUT:", res.stdout)
    else:
        print(f"❌ Could not find codebase-memory-mcp executable at: {mcp_exe}")
        sys.exit(1)

if __name__ == "__main__":
    main()
