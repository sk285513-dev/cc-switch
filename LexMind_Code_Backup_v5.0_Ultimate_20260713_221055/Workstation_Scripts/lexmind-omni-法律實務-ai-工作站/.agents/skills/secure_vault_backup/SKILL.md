---
name: secure-vault-backup
description: Manages secure AES-256 Fernet encrypted backup and restore archives of the legal databases. Use this skill when adjusting backup paths or encryption keys.
---

# Secure Vault Backup Agent Skill

This skill defines the database backup and AES-256 encryption policies.

## File Locations
- **Backup Core**: `C:/LocalAI_Workstation/scripts/backup_manager.py` (`LegalDBBackupManager`)

---

## Agent Guidelines & Tuning

1. **Encrypted Archive**:
   - Compresses ChromaDB dataset folders and database JSONs into a ZIP archive.
   - Encrypts the ZIP byte-stream using AES-256 (Fernet module).
   - Manages a rolling 14-day history retention limit.
