---
name: lexmind-timeout-tester
description: >-
  Automated test utility to validate LexMind-Omni file parsing API, dynamic timeout scaling, and process tree termination (taskkill) on Windows. Supports testing with a 5GB sparse file and auto-starting the server.
---

# LexMind-Omni Timeout & Process Tree Killer Tester

## Overview
This skill provides automated verification commands to test the large file parsing timeout mechanism and subprocess process-tree termination on Windows. It works by creating a 0-disk-space 5GB sparse file, sending a request with an overridden short timeout parameter, and verifying the expected HTTP 504 Gateway Timeout return code, while ensuring all background processes (Whisper, CUDA, ffmpeg) are forcefully killed via `taskkill`.

## Dependencies
- None. This is a standalone test utility utilizing the python standard library and `requests`.

## Quick Start
Check if the server is running or start it automatically, and run the timeout test:

```bash
# 1. Check/Start the local LexMind-Omni server
uv run C:/Users/temp/.gemini/config/skills/lexmind-timeout-tester/scripts/run_test.py check-server

# 2. Run the timeout test with a 5GB sparse file and output the report
uv run C:/Users/temp/.gemini/config/skills/lexmind-timeout-tester/scripts/run_test.py run-test --output C:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/data/test_report.json

# 3. Run the vault CRUD integration test and output the report
uv run C:/Users/temp/.gemini/config/skills/lexmind-timeout-tester/scripts/run_test.py run-vault-test --output C:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/data/vault_test_report.json
```

## Utility Scripts

### `check-server`
Verifies whether the target server (default: port 3000) is online. If offline, it automatically triggers `npm run dev` in the background within the workspace and waits up to 30 seconds for it to bind.

**Parameters**:
- `--workspace` (optional): Path to the workspace directory. Defaults to `c:\Users\temp\antigravity\LexMind-Omni-法律實務-AI-工作站`.
- `--port` (optional): Server listening port. Defaults to `3000`.
- `--timeout` (optional): Maximum wait seconds for the server to start. Defaults to `30`.

### `run-test`
Creates a 5GB sparse file, overrides the timeout to 3 seconds, triggers the backend parser API, verifies the HTTP 504 response, and cleans up the test file.

**Parameters**:
- `--workspace` (optional): Path to the workspace. Defaults to `c:\Users\temp\antigravity\LexMind-Omni-法律實務-AI-工作站`.
- `--port` (optional): Server port. Defaults to `3000`.
- `--file-size-mb` (optional): Test file size in MB. Defaults to `5120` (5GB).
- `--test-timeout-ms` (optional): Override timeout in milliseconds. Defaults to `3000` (3 seconds).
- `--output` (required): Absolute path to save the generated JSON test report.

### `run-vault-test`
Tests the complete CRUD integration of the intelligence vault on the server (GET vault list, POST ingest a dummy text, verify vault list, PUT update dummy text and category, verify vault database persistence, DELETE dummy text, verify vault deletion).

**Parameters**:
- `--workspace` (optional): Path to the workspace. Defaults to `c:\Users\temp\antigravity\LexMind-Omni-法律實務-AI-工作站`.
- `--port` (optional): Server port. Defaults to `3000`.
- `--output` (required): Absolute path to save the generated JSON test report.

## Rate Limiting
No rate limiting applies as all API calls are executed against the local loopback interface (`127.0.0.1`).

## Common Mistakes
1. **Wrong Workspace Path**: Ensure that the workspace directory is correct (contains `package.json` and the `.env` settings) when using the `check-server` auto-boot command.
2. **Missing Output File Parameter**: The `--output` parameter in `run-test` and `run-vault-test` is strictly required. Ensure you provide a writable absolute path.
