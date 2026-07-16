---
name: mapreduce-corrector
description: Handles MapReduce long text chunking and parallel synthesis for LLM transcript proofreading. Use this skill when modifying text partitioning, chunk sizes, or concurrency parameters.
---

# MapReduce Corrector Agent Skill

This skill defines the responsibilities and guidelines for the dedicated MapReduce Corrector Agent, which manages the chunked proofreading and synthesis of long transcript facts using local LLM models.

## File Locations
- **Backend API Implementation**: [server.ts](file:///c:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/server.ts) (implements `/api/ingest` and long text MapReduce helper functions)

---

## Agent Guidelines & Tuning

1. **Text Chunking (`splitTextIntoChunks`)**:
   - Splits transcripts into segments of approximately 4,000 characters.
   - Must align splits strictly at line/newline boundaries to avoid breaking timestamps (e.g., `[00:01:23 -> 00:01:28]`).

2. **Parallel Processing (`processChunksInParallel`)**:
   - Sends segments to the LLM servers in parallel.
   - Max concurrent requests: `3` (to avoid throttling or Ollama resource exhaustion).
   - Intercepts and merges results in the original order.

3. **High-Fidelity Fallback**:
   - If a segment fails to correct due to an LLM timeout, fall back to the original text for that segment. Do not discard the transcript.

4. **ASR Bypass for Large Transcripts**:
   - For transcripts exceeding 4,000 characters, bypass Gemini word-for-word correction to prevent truncation. Rely on Whisper's rule-corrected output, while allowing the summarizer up to 25,000 characters.
