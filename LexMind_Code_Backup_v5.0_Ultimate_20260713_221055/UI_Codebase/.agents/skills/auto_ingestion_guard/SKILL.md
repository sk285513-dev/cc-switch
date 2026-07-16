---
name: auto-ingestion-guard
description: Scans local media files, hashes them for duplicate check, validates content relevance, and invokes ASR/OCR/LLM. Use this skill when tuning background scan paths or file formats.
---

# Auto Ingestion Guard Agent Skill

This skill defines the background file scanner and memory crawler policies.

## File Locations
- **Scanner Core**: `C:/LocalAI_Workstation/scripts/auto_ingest_bot.py` (`auto_ingest_bot.py`)

---

## Agent Guidelines & Tuning

1. **Duplicate Guard**:
   - Computes SHA-256 file hashes and matches them against existing vault database keys.
   - Automatically skips processed files instantly to conserve GPU.

2. **Relevance Filter**:
   - Runs files through filename and header validation to filter out game logs or non-legal documents.
