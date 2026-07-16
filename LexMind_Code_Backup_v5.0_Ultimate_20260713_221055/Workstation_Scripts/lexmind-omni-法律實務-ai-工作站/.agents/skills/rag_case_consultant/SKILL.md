---
name: rag-case-consultant
description: Handles case consultation, RWS (實務動態權重系統), legal reasoning using syllogism, and warning messages for statute of limitations. Use this skill when modifying retrieval weights, legal prompts, or dialogue memory.
---

# RAG Case Consultant Agent Skill

This skill defines the rules for the core legal reasoning and case consultation agent, which leverages the RWS weight system to answer case questions.

## File Locations
- **RAG & Analyzer Core**: `C:/LocalAI_Workstation/scripts/agent_core_pro.py` (defines `LocalLegalAgent` and `LegalRWSAnalyzer`)

---

## Agent Guidelines & Tuning

1. **RWS (實務動態權重系統)**:
   - Level 1 (Constitution / Supreme Court Precedents): weight multiplier = 1.0.
   - Level 2 (Acts/Statutes): weight multiplier = 0.8.
   - Level 3 (Executive Orders/Rules): weight multiplier = 0.5.
   - Level 4/5 (Others): weight multiplier = 0.2.
   - RWS scores are combined with cosine similarity vectors (`0.4 * sim + 0.6 * rws`) to re-rank results.

2. **Statute of Limitations Defense Warning**:
   - If the user's question contains statute keywords (e.g., "時效", "幾年", "請求權"), the agent must inject a prominent bold red warning at the very beginning of the response.

3. **Taiwan Legal Terminology Enforcement**:
   - Responses must strictly use official Taiwan legal terms (e.g., "被告", "檢察官", "起訴") and completely avoid Mainland terms (e.g., "被告人", "檢察院", "公安").
