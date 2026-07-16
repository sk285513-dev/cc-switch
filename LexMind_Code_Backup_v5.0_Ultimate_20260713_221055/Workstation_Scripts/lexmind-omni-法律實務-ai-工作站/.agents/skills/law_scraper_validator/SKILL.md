---
name: law-scraper-validator
description: Scrapes latest law regulations and exam questions, filtering content based on legal keyword density. Use this skill when adding scraping domains or keyword thresholds.
---

# Law Scraper Validator Agent Skill

This skill defines crawler regulations and legal-content validation checks.

## File Locations
- **Scraper Core**: `C:/LocalAI_Workstation/scripts/law_scraper_cli.py` (`law_scraper_cli.py`)

---

## Agent Guidelines & Tuning

1. **Legal Validation**:
   - Filters out non-legal pages by checking regular expression patterns for case numbers (e.g., `\d+ 年 [^\d\s]+ 字第 \d+ 號`) and legal keyword frequencies (e.g., "民法", "刑法", "侵權", "時效").
   - Restricts crawling strictly to legitimate law databases or sites containing relevant search criteria.
