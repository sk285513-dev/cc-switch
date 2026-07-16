---
name: visual-blackboard-analyzer
description: Detects contours of charts in documents and tracks blackboard updates in video streams using OpenCV, generating Mermaid diagrams. Use this skill when adjusting OpenCV thresholds or Mermaid templates.
---

# Visual Blackboard Analyzer Agent Skill

This skill defines visual analyzing behaviors, including OpenCV logic for extracting logic diagrams and analyzing blackboard board-writings in videos.

## File Locations
- **Visual Core**: `C:/LocalAI_Workstation/scripts/visual_analyzer.py` (`VisualLegalAnalyzer`)

---

## Agent Guidelines & Tuning

1. **Document Chart Contours**:
   - Thresholding and contour analysis are used to identify blocks larger than `150x150` pixels.
   - Cropped images are saved in `Obsidian_Vault/04_教材圖表校對/images/`.

2. **Video Blackboard Frame Differencing**:
   - Video frames are sampled every 5 seconds.
   - Pixel delta > 0.8% indicates the instructor is writing.
   - When the delta falls below 0.15% (and 30s have elapsed), it triggers a board capture.
   - Text board OCR is analyzed by LLM; relational board diagrams generate Mermaid.js codes.
