---
name: exam-adversarial-trainer
description: Generates legal exam answers and critiques them through a professor-student adversarial loop. Use this skill when modifying question-solving prompts or grading rubrics.
---

# Exam Adversarial Trainer Agent Skill

This skill defines the professor-student adversarial answering loop.

## File Locations
- **Exam Core**: `C:/LocalAI_Workstation/scripts/exam_trainer.py` (`ExamTrainer`)

---

## Agent Guidelines & Tuning

1. **Solve and Critique Loop**:
   - Generates answers using Taiwan legal syllogism (三段論法).
   - An adversarial professor agent reviews the candidate answer, checks for legal reasoning issues, and writes a detailed critique.
   - Saves the critique in `database.json` as a Lesson Learned item.
