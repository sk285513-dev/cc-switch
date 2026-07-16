---
name: knowledge-deep-digester
description: Digests large legal documents and transcripts into core issues, judge reasoning, and case conclusions using the local LLM. Use this skill when modifying synthesis prompts or digest formats.
---

# Knowledge Deep Digester Agent Skill

This skill defines the rules for synthesizing legal files and lecture scripts into legal insights.

## File Locations
- **Digest Engine**: `C:/LocalAI_Workstation/scripts/law_digester.py` (`LawDigesterPro`)

---

## Agent Guidelines & Tuning

1. **Segment Digestion**:
   - Splices raw documents into 2000-character segments with 150-character overlaps.
   - Prompts the LLM to extract:
     1. 核心法律爭點 (Core Legal Issues)
     2. 法官/學者推論邏輯與法條引用 (Reasoning & Citations)
     3. 最終實務結論 (Conclusion/Action Point)

2. **Database Storage**:
   - Integrates the original paragraph text and the digested insights, writing them back to the vector vault.
