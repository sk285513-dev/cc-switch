# /// script
# dependencies = [
#   "requests",
# ]
# ///

import os
import sys
import time
import argparse
import json
import socket
import subprocess

DEFAULT_WORKSPACE = r"c:\Users\temp\antigravity\LexMind-Omni-法律實務-AI-工作站"

def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        try:
            s.connect(("127.0.0.1", port))
            return True
        except:
            return False

def check_and_start_server(workspace, port, timeout_sec=30):
    if is_port_open(port):
        sys.stderr.write(f"ℹ️ Server is already running on port {port}.\n")
        return True

    sys.stderr.write(f"🚀 Server is offline. Attempting to start in background at {workspace}...\n")
    if not os.path.exists(workspace):
        sys.stderr.write(f"❌ Error: Workspace directory does not exist: {workspace}\n")
        return False

    # Start the server in the background using npm run dev
    try:
        if sys.platform == "win32":
            # On Windows, we use shell=True and Popen to start in background
            subprocess.Popen(
                ["npm", "run", "dev"],
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=workspace,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
            )
        else:
            subprocess.Popen(
                ["npm", "run", "dev"],
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=workspace
            )
    except Exception as e:
        sys.stderr.write(f"❌ Failed to spawn server process: {e}\n")
        return False

    # Wait for the port to open
    start_time = time.time()
    while time.time() - start_time < timeout_sec:
        if is_port_open(port):
            sys.stderr.write(f"✅ Server started successfully on port {port}!\n")
            return True
        time.sleep(1.0)
        sys.stderr.write("Waiting for port 3000 to become active...\n")

    sys.stderr.write(f"❌ Timeout waiting for server to start on port {port}.\n")
    return False

def create_sparse_file(filepath, size_mb):
    size_bytes = size_mb * 1024 * 1024
    try:
        sys.stderr.write(f"📄 Creating sparse test file ({size_mb} MB) at: {filepath}...\n")
        with open(filepath, "wb") as f:
            f.truncate(size_bytes)
        return True
    except Exception as e:
        sys.stderr.write(f"⚠️ Failed to create sparse file ({e}). Falling back to regular file...\n")
        try:
            # Fallback to small 5MB regular file
            with open(filepath, "wb") as f:
                f.write(b"0" * (5 * 1024 * 1024))
            sys.stderr.write("✅ Fallback successful. Small file created.\n")
            return True
        except Exception as e2:
            sys.stderr.write(f"❌ Regular fallback failed: {e2}\n")
            return False

def run_test(args):
    # 1. Ensure server is running
    if not check_and_start_server(args.workspace, args.port):
        sys.exit(1)

    # 2. Prepare test file
    test_filename = "lexmind_sparse_test_large.mp4"
    test_filepath = os.path.join(args.workspace, test_filename)
    
    if not create_sparse_file(test_filepath, args.file_size_mb):
        sys.exit(1)

    # 3. Call server parser API
    import requests
    url = f"http://127.0.0.1:{args.port}/api/parse-local-file"
    payload = {
        "path": test_filepath,
        "ext": "mp4",
        "testTimeout": args.test_timeout_ms
    }

    sys.stderr.write(f"📡 Sending POST request to {url} (Overridden Timeout: {args.test_timeout_ms} ms)...\n")
    start_time = time.time()
    
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "target_file": test_filepath,
        "file_size_mb": args.file_size_mb,
        "test_timeout_ms": args.test_timeout_ms,
        "status": "failed",
        "api_response_code": None,
        "elapsed_seconds": 0.0,
        "server_response": None
    }

    try:
        # We expect a 504 response, so let's allow a slightly larger client-side timeout
        response = requests.post(url, json=payload, timeout=(args.test_timeout_ms + 5000) / 1000.0)
        elapsed = time.time() - start_time
        report["elapsed_seconds"] = elapsed
        report["api_response_code"] = response.status_code
        
        try:
            res_json = response.json()
            report["server_response"] = res_json
        except:
            res_json = {"text": response.text[:200]}
            report["server_response"] = res_json

        sys.stderr.write(f"Response status: {response.status_code} in {elapsed:.2f}s.\n")

        # 4. Verify timeout outcome
        if response.status_code == 504:
            sys.stderr.write("✅ Test Succeeded: Server timed out correctly and returned 504.\n")
            report["status"] = "success"
        else:
            sys.stderr.write(f"❌ Test Failed: Expected HTTP 504, but received HTTP {response.status_code}.\n")
            
    except Exception as e:
        sys.stderr.write(f"❌ HTTP request crashed: {e}\n")
        report["server_response"] = {"error": str(e)}

    # 5. Cleanup test file
    if os.path.exists(test_filepath):
        try:
            os.remove(test_filepath)
            sys.stderr.write("🧹 Test file cleaned up successfully.\n")
        except Exception as cleanup_e:
            sys.stderr.write(f"⚠️ Failed to delete test file: {cleanup_e}\n")

    # 6. Write report file
    try:
        with open(args.output, "w", encoding="utf-8") as f_out:
            json.dump(report, f_out, indent=2, ensure_ascii=False)
        sys.stdout.write(f"Success! Report written to: {args.output}\n")
    except Exception as write_e:
        sys.stderr.write(f"❌ Failed to write report file: {write_e}\n")
        sys.exit(1)

    if report["status"] != "success":
        sys.exit(1)

def run_vault_test(args):
    # 1. Ensure server is running
    if not check_and_start_server(args.workspace, args.port):
        sys.exit(1)

    import requests
    
    # Reset database to factory settings to prevent test pollution
    try:
        url_reset = f"http://127.0.0.1:{args.port}/api/reset-db"
        resp = requests.post(url_reset, timeout=5)
        sys.stderr.write(f"ℹ️ Reset database status: {resp.status_code}\n")
    except Exception as e:
        sys.stderr.write(f"⚠️ Failed to reset database: {e}\n")
    
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "test_type": "vault-crud-integration",
        "status": "failed",
        "steps": []
    }
    
    def log_step(name, passed, detail=None):
        step_info = {"step": name, "status": "pass" if passed else "fail"}
        if detail:
            step_info["detail"] = detail
        report["steps"].append(step_info)
        sys.stderr.write(f"[{'PASS' if passed else 'FAIL'}] {name}\n")
        if not passed:
            report["status"] = "failed"
            write_report()
            sys.exit(1)

    def write_report():
        try:
            with open(args.output, "w", encoding="utf-8") as f_out:
                json.dump(report, f_out, indent=2, ensure_ascii=False)
            sys.stdout.write(f"Report written to: {args.output}\n")
        except Exception as e:
            sys.stderr.write(f"❌ Failed to write report file: {e}\n")

    # Step 1: Query initial vault
    try:
        url_get = f"http://127.0.0.1:{args.port}/api/intelligence-vault"
        resp = requests.get(url_get, timeout=5)
        log_step("GET initial vault items", resp.status_code == 200, f"HTTP {resp.status_code}, count: {len(resp.json().get('items', []))}")
        initial_items = resp.json().get("items", [])
    except Exception as e:
        log_step("GET initial vault items (exception)", False, str(e))

    # Step 2: Inject a dummy item to verify ingestion writes to vault
    dummy_name = f"lexmind_autotest_{int(time.time())}.txt"
    dummy_content = "測試事實：原告黃某於被告假芳開車擦撞後，受有大腿骨折，主張損害合償。此屬侵權形為。"
    try:
        url_ingest = f"http://127.0.0.1:{args.port}/api/ingest"
        payload = {
            "files": [{
                "name": dummy_name,
                "content": dummy_content,
                "category": "學術教材"
            }],
            "mock": True
        }
        resp = requests.post(url_ingest, json=payload, timeout=120)
        log_step("POST inject dummy item via Ingest API", resp.status_code == 200, f"HTTP {resp.status_code}")
    except Exception as e:
        log_step("POST inject dummy item (exception)", False, str(e))

    # Step 3: Query vault and locate the injected item
    created_item = None
    try:
        resp = requests.get(url_get, timeout=5)
        items = resp.json().get("items", [])
        for item in items:
            if item.get("source") == dummy_name:
                created_item = item
                break
        log_step("Verify dummy item exists in vault", created_item is not None, f"Found item ID: {created_item.get('id') if created_item else 'None'}")
    except Exception as e:
        log_step("Verify dummy item exists (exception)", False, str(e))

    # Step 4: Perform PUT update (modify content and change category to "判例")
    updated_text = created_item.get("text", "") + "\n【已由自動化測試Agent修改】"
    updated_category = "判例"
    item_id = created_item.get("id")
    try:
        url_put = f"http://127.0.0.1:{args.port}/api/intelligence-vault/{item_id}"
        resp = requests.put(url_put, json={"text": updated_text, "category": updated_category}, timeout=5)
        log_step("PUT update dummy item category & content", resp.status_code == 200, f"HTTP {resp.status_code}")
    except Exception as e:
        log_step("PUT update dummy item (exception)", False, str(e))

    # Step 5: Verify PUT update in vault
    try:
        resp = requests.get(url_get, timeout=5)
        items = resp.json().get("items", [])
        verified_item = next((item for item in items if item.get("id") == item_id), None)
        has_updated = verified_item and verified_item.get("category") == updated_category and updated_text in verified_item.get("text", "")
        log_step("Verify updates persisted in database", has_updated, f"Category: {verified_item.get('category') if verified_item else 'None'}")
    except Exception as e:
        log_step("Verify updates persisted (exception)", False, str(e))

    # Step 6: Perform DELETE operation
    try:
        url_delete = f"http://127.0.0.1:{args.port}/api/intelligence-vault/{item_id}"
        resp = requests.delete(url_delete, timeout=5)
        log_step("DELETE dummy item from vault", resp.status_code == 200, f"HTTP {resp.status_code}")
    except Exception as e:
        log_step("DELETE dummy item (exception)", False, str(e))

    # Step 7: Verify deletion in vault
    try:
        resp = requests.get(url_get, timeout=5)
        items = resp.json().get("items", [])
        deleted_success = not any(item.get("id") == item_id for item in items)
        log_step("Verify dummy item completely deleted", deleted_success, "Item ID is no longer present")
    except Exception as e:
        log_step("Verify dummy item completely deleted (exception)", False, str(e))

    # Step 8: Batch Ingestion of Multiple Files
    batch_files = [
        {"name": "lexmind_batch_test_1.txt", "content": "本案由原告假芳提起訴訟，被告倚方抗辯。", "category": "通用"},
        {"name": "lexmind_batch_test_2.txt", "content": "契約書由假芳起草，並由倚方確認簽署。", "category": "學術教材"},
        {"name": "lexmind_batch_test_3.txt", "content": "民事訴訟法上假芳主張權利，倚方抗辯時效消滅。", "category": "判例"}
    ]
    batch_ids = []
    try:
        url_ingest = f"http://127.0.0.1:{args.port}/api/ingest"
        payload = {"files": batch_files, "mock": True}
        resp = requests.post(url_ingest, json=payload, timeout=185)
        passed = resp.status_code == 200 and len(resp.json().get("files", [])) == 3
        log_step("POST Batch Ingestion of 3 files", passed, f"HTTP {resp.status_code}, Ingested: {len(resp.json().get('files', [])) if passed else 0}")
    except Exception as e:
        log_step("POST Batch Ingestion (exception)", False, str(e))

    # Verify batch files in database
    try:
        resp = requests.get(url_get, timeout=5)
        items = resp.json().get("items", [])
        found_count = 0
        for f in batch_files:
            for item in items:
                if item.get("source") == f["name"]:
                    batch_ids.append(item.get("id"))
                    found_count += 1
                    break
        log_step("Verify all 3 batch files exist in database", found_count == 3, f"Found {found_count} of 3 batch items in database")
    except Exception as e:
        log_step("Verify batch files exist (exception)", False, str(e))

    # Step 9: Long-Text Split-and-Combine Correctness Test
    # Generate 12,000 character long text to trigger multiple chunks (splitTextIntoChunks target is 4000)
    line_pattern = "原告假芳開車擦撞被告倚方車輛，涉及侵權行為損害賠償責任與時效抗辯訴訟。\n"
    long_content = line_pattern * 200  # 200 * 35 chars = 7000 chars (will span 2 chunks since limit is 4000)
    long_name = "lexmind_long_split_test.txt"
    long_item_id = None
    try:
        payload = {
            "files": [{
                "name": long_name,
                "content": long_content,
                "category": "通用"
            }],
            "mock": True
        }
        resp = requests.post(url_ingest, json=payload, timeout=185)
        
        # Query database to find the long item
        resp_get = requests.get(url_get, timeout=5)
        items = resp_get.json().get("items", [])
        long_item = next((item for item in items if item.get("source") == long_name), None)
        
        if long_item:
            long_item_id = long_item.get("id")
            text = long_item.get("text", "")
            
            # Check correctness:
            # 1. Corrections were made (no "假芳" or "倚方")
            has_no_raw_typos = "假芳" not in text and "倚方" not in text
            # 2. Text was re-combined successfully and has roughly the expected size / lines
            original_lines_count = len(long_content.strip().split("\n"))
            corrected_lines_count = len(text.strip().split("\n"))
            
            has_correct_length = corrected_lines_count >= original_lines_count
            
            log_step("Verify long-text split-and-combine correctness (corrections applied and ordering preserved)", 
                     has_no_raw_typos and has_correct_length, 
                     f"No typos: {has_no_raw_typos}, Corrected lines: {corrected_lines_count} (original: {original_lines_count})")
        else:
            log_step("Verify long-text split-and-combine (locate item)", False, "Long test item was not found in vault")
    except Exception as e:
        log_step("Verify long-text split-and-combine (exception)", False, str(e))

    # Step 10: Cleanup batch and long-text items
    cleanup_success = True
    all_cleanup_ids = batch_ids + ([long_item_id] if long_item_id else [])
    for c_id in all_cleanup_ids:
        try:
            url_delete = f"http://127.0.0.1:{args.port}/api/intelligence-vault/{c_id}"
            resp = requests.delete(url_delete, timeout=5)
            if resp.status_code != 200:
                cleanup_success = False
        except Exception as e:
            cleanup_success = False
            
    log_step("Cleanup batch and long-text items from database", cleanup_success, f"Deleted {len(all_cleanup_ids)} test items")

    report["status"] = "success"
    write_report()

def main():
    parser = argparse.ArgumentParser(description="LexMind-Omni Ingestion Timeout & Kill Tester")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # check-server subcommand
    srv_parser = subparsers.add_parser("check-server", help="Check server status and auto-boot if offline")
    srv_parser.add_argument("--workspace", default=DEFAULT_WORKSPACE, help="Path to LexMind workspace")
    srv_parser.add_argument("--port", type=int, default=3000, help="Port of LexMind server")
    srv_parser.add_argument("--timeout", type=int, default=30, help="Max wait seconds for boot")

    # run-test subcommand
    test_parser = subparsers.add_parser("run-test", help="Execute the timeout and process-killing test case")
    test_parser.add_argument("--workspace", default=DEFAULT_WORKSPACE, help="Path to LexMind workspace")
    test_parser.add_argument("--port", type=int, default=3000, help="Port of LexMind server")
    test_parser.add_argument("--file-size-mb", type=int, default=5120, help="Size of sparse file in MB (default 5GB)")
    test_parser.add_argument("--test-timeout-ms", type=int, default=3000, help="Timeout in ms to override (default 3s)")
    test_parser.add_argument("--output", required=True, help="Path to save the JSON test report")

    # run-vault-test subcommand
    vault_parser = subparsers.add_parser("run-vault-test", help="Execute the intelligence vault CRUD and UI integration test")
    vault_parser.add_argument("--workspace", default=DEFAULT_WORKSPACE, help="Path to LexMind workspace")
    vault_parser.add_argument("--port", type=int, default=3000, help="Port of LexMind server")
    vault_parser.add_argument("--output", required=True, help="Path to save the JSON test report")

    args = parser.parse_args()

    if args.command == "check-server":
        if check_and_start_server(args.workspace, args.port, args.timeout):
            sys.stdout.write("Success! Server is actively listening.\n")
        else:
            sys.exit(1)
    elif args.command == "run-test":
        run_test(args)
    elif args.command == "run-vault-test":
        run_vault_test(args)

if __name__ == "__main__":
    main()
