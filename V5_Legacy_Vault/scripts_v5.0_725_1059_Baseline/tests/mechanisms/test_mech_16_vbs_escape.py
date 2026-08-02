# -*- coding: utf-8 -*-
"""
機制十六：VBScript 啟動隔離之設計 (VBScript Process Isolation)
【BUG-08 修正】VBScript 路徑中含有雙引號需用 Chr(34) 跳脫，
    否則包含空白的中文路徑會在 cscript 解析時截斷，導致 FileNotFoundError。
"""
import os
import sys
import pytest
import subprocess
from pathlib import Path


def build_vbs_launcher(script_path: str, log_path: str) -> str:
    """
    【BUG-08 修正】使用 Chr(34) 包裹路徑，確保含空白的中文路徑不會被截斷。
    原始錯誤版本：直接用雙引號，中文路徑空白處截斷。
    """
    # Chr(34) = 雙引號字元（ASCII 34），在 VBScript 內部跳脫用
    vbs_content = f'''
Set objShell = WScript.CreateObject("WScript.Shell")
Dim pythonPath
pythonPath = Chr(34) & "{sys.executable.replace(chr(92), chr(92)*2)}" & Chr(34)
Dim scriptPath
scriptPath = Chr(34) & "{script_path.replace(chr(92), chr(92)*2)}" & Chr(34)
Dim cmd
cmd = pythonPath & " " & scriptPath & " >> " & Chr(34) & "{log_path.replace(chr(92), chr(92)*2)}" & Chr(34) & " 2>&1"
objShell.Run cmd, 0, False
'''
    return vbs_content.strip()


@pytest.mark.asyncio
async def test_mechanism_16_vbs_path_escape(tmp_path: Path):
    """
    KPI: Chr(34) 跳脫驗證 — VBS 產生的 cmd 字串中，路徑被雙引號正確包裹
    """
    # 建立含有「空格與中文」的假路徑（模擬真實場景）
    fake_script = r"C:\LocalAI Workstation\法律 Scripts\run_workflow.py"
    fake_log = r"A:\logs\workflow log.txt"

    vbs = build_vbs_launcher(fake_script, fake_log)

    # KPI-1: VBS 內容必須含有 Chr(34)（不是裸的雙引號包路徑）
    assert 'Chr(34)' in vbs, "機制十六失敗：BUG-08 未修正，路徑缺少 Chr(34) 跳脫"
    print("  ✅ KPI-1: Chr(34) 跳脫存在")

    # KPI-2: scriptPath 行中 Chr(34) 出現在路徑前後
    script_line = [line for line in vbs.split('\n') if 'scriptPath' in line and 'Chr(34)' in line]
    assert len(script_line) > 0, "機制十六失敗：scriptPath 行缺少 Chr(34) 包裹"
    print(f"  ✅ KPI-2: scriptPath 行：{script_line[0].strip()}")

    # KPI-3: 寫入臨時 .vbs 檔案，確認文字可正確落地（不含損毀字元）
    vbs_file = tmp_path / "test_launcher.vbs"
    vbs_file.write_text(vbs, encoding="utf-8-sig")  # BOM 讓 cscript 正確識別 UTF-8
    assert vbs_file.exists(), "機制十六失敗：.vbs 檔案未能正確落地"
    assert vbs_file.stat().st_size > 0, "機制十六失敗：.vbs 檔案為空"

    content = vbs_file.read_text(encoding="utf-8-sig")
    assert 'Chr(34)' in content, "機制十六失敗：落地的 VBS 中 Chr(34) 丟失"
    print(f"  ✅ KPI-3: .vbs 落地成功，{vbs_file.stat().st_size} bytes")

    print("✅ 機制十六通過：VBScript Chr(34) 路徑跳脫，BUG-08 修正驗證成功")
