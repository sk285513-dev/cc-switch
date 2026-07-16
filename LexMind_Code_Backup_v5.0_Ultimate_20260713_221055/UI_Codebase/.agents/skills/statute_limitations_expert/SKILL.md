---
name: statute-limitations-expert
description: Performs calculations of statute of limitations and deadlines for civil and administrative law. Use this skill when modifying statutory rules or adding new litigation time limits.
---

# Statute Limitations Expert Agent Skill

This skill defines the rules for calculating legal time limits and litigation deadlines under Taiwan statutory regulations.

## File Locations
- **Time Limits Module**: `C:/LocalAI_Workstation/scripts/legal_calendar.py` (`LegalCalendarPlugin`)

---

## Agent Guidelines & Tuning

1. **Computation Principles**:
   - **Start Date (始日不算入)**: The event day itself is excluded. Computation begins on the next day (Civil Code §120-2).
   - **Holiday Extension (末日順延)**: If the deadline falls on a Sunday, national holiday, or day of rest, it is extended to the next business day (Civil Code §122).

2. **Supported Statutes**:
   - `civil_tort`: 2 years (Civil Code §197).
   - `civil_general`: 15 years (Civil Code §125).
   - `public_wage`: 5 years (Administrative law / salaries).
   - `labor_30d`: 30 days (Labor Standards Act §14).

3. **Modifications & Tuning**:
   - All rules regarding time limits, calendar arithmetic, and holiday databases must reside inside `legal_calendar.py`. Do not place raw calculations in UI controllers.
