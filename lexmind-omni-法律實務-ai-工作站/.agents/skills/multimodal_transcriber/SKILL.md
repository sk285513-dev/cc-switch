---
name: multimodal-transcriber
description: Performs audio transcription and document image OCR using faster-whisper and pytesseract, correcting recognition errors with a rule-based dictionary. Use this skill when tuning Whisper parameters or glossary rules.
---

# Multimodal Transcriber Agent Skill

This skill defines the rules for audio transcription (ASR) and document OCR processing.

## File Locations
- **ASR & OCR Engine**: `C:/LocalAI_Workstation/scripts/multimodal_input.py` (`MultimodalLegalInput`)
- **Glossary Dictionary**: `C:/LocalAI_Workstation/legal_glossary.json` (contains common dict mappings)

---

## Agent Guidelines & Tuning

1. **Whisper ASR Chunking**:
   - Large audio/video files (extracting WAV > 30MB) are automatically sliced into 15-minute segments using `ffmpeg` to prevent OOM errors.
   - Slices are processed sequentially and merged back, with timestamps shifted.

2. **WAV Temp Drive Fallback**:
   - Temporary WAV files are written in the file's parent directory.
   - If read-only, it falls back to drive `A:/LexMind_Temp`.
   - If A drive is unavailable, it falls back to the system temp folder.

3. **Glossary Calibration**:
   - The transcriber loads `legal_glossary.json` to replace common homophone misrecognitions (e.g., "假芳" -> "甲方", "消滅時效" -> "消滅時效").
