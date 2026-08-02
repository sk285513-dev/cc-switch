#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_highway_bypass.py
========================
金鑰調度架構重構："高速公路與私家車分流"

問題：run_workflow.py 無條件初始化 QuotaManager 盤查私家金鑰 (config/keys.yaml)，
      即使 config.yaml 已設定 stt_engine: vertexai（企業高速公路），
      個人金鑰損壞/遺失時仍會拋出 NO VALID GEMINI API KEYS FOUND 導致崩潰。

修正：讀取 config.yaml 的 stt_engine 值。
      - vertexai → 印出提示，跳過 QuotaManager 初始化，qm = None
      - gemini   → 維持原邏輯，正常初始化 QuotaManager

安全措施：
- 純 Python open(encoding='utf-8') 讀寫，不用 PowerShell 正則，避免中文注釋編碼損壞
- 套用前自動建立時間戳備份 (.bak.YYYYMMDDHHMMSS)
- 找不到預期模式時，警告並跳過，不強行寫入
"""

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path("C:/LocalAI_Workstation")
WORKFLOW_PY = ROOT / "scripts" / "run_workflow.py"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


def backup(filepath: Path) -> Path:
    bak = filepath.with_name(f"{filepath.name}.bak.{STAMP}")
    shutil.copy2(filepath, bak)
    print(f"Backed up: {filepath} -> {bak}")
    return bak


def patch_workflow(filepath: Path) -> bool:
    content = filepath.read_text(encoding="utf-8")

    pattern = re.compile(
        r'(?P<indent>[ \t]*)qm\s*=\s*QuotaManager\(\)\s*\n'
    )

    match = pattern.search(content)
    if not match:
        print("WARNING: 找不到 'qm = QuotaManager()' 這一行，未做任何修改。請人工檢查。")
        return False

    indent = match.group("indent")
    replacement = (
        f"{indent}stt_engine = str(config.get('stt_engine', 'gemini')).strip().lower()\n"
        f"{indent}if stt_engine == 'vertexai':\n"
        f"{indent}    print(\"[INFO] 系統走企業高速公路，跳過 QuotaManager 私家金鑰盤查\")\n"
        f"{indent}    qm = None\n"
        f"{indent}else:\n"
        f"{indent}    qm = QuotaManager()\n"
    )

    new_content = content[:match.start()] + replacement + content[match.end():]

    preceding = content[:match.start()]
    if not re.search(r'\bconfig\s*=', preceding):
        print("WARNING: 在 qm = QuotaManager() 之前找不到 'config' 變數的定義。")
        print("         請確認 config.yaml 已在此作用域內被載入為 'config' 變數，")
        print("         否則此補丁會導致 NameError。已中止寫入，未做任何修改。")
        return False

    filepath.write_text(new_content, encoding="utf-8")
    print(f"PATCHED: {filepath}")
    print("--- 新增內容預覽 ---")
    print(replacement)
    return True


def main():
    if not WORKFLOW_PY.exists():
        print(f"ERROR: 找不到檔案 {WORKFLOW_PY}")
        sys.exit(1)

    backup(WORKFLOW_PY)
    ok = patch_workflow(WORKFLOW_PY)

    if ok:
        print("\n=== 套用完成 ===")
        print("下一步：")
        print(f'  1. Select-String -Path "{WORKFLOW_PY}" -Pattern "企業高速公路"')
        print(f'  2. python "{WORKFLOW_PY}" --one-shot')
        print("  3. 確認 config.yaml 中 stt_engine: vertexai 時，終端印出對應提示且不崩潰")
    else:
        print("\n=== 未套用任何修改，請人工檢查上方 WARNING 訊息 ===")


if __name__ == "__main__":
    main()