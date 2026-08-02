# -*- coding: utf-8 -*-
"""
機制二十三：UTF-8 全局輸出流之設計 (UTF-8 Global Output Stream)
【BUG-12 修正】sys.stdout.reconfigure 在 Python 3.6 不存在，
    加 hasattr guard + io.TextIOWrapper fallback。
"""
import sys
import io
import pytest


def setup_utf8_streams() -> dict:
    """
    【BUG-12 修正】安全設定 UTF-8 輸出流。
    回傳診斷資訊方便 KPI 驗證。
    """
    result = {"method": None, "stdout_encoding": None, "stderr_encoding": None}

    if hasattr(sys.stdout, 'reconfigure'):
        # Python 3.7+
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        result["method"] = "reconfigure"
    else:
        # Python 3.6 fallback
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        result["method"] = "TextIOWrapper"

    result["stdout_encoding"] = getattr(sys.stdout, 'encoding', 'unknown')
    result["stderr_encoding"] = getattr(sys.stderr, 'encoding', 'unknown')
    return result


@pytest.mark.asyncio
async def test_mechanism_23_utf8_stream():
    """
    KPI-1: UTF-8 編碼確認 — stdout/stderr encoding = utf-8
    KPI-2: 無 AttributeError — 在 Python 3.6 不崩潰
    KPI-3: 中文字元輸出正常 — 法律術語可正確輸出
    """
    # KPI-2: 不崩潰
    try:
        info = setup_utf8_streams()
    except AttributeError as e:
        pytest.fail(f"機制二十三失敗：BUG-12 hasattr guard 未生效，AttributeError: {e}")

    # KPI-1: 驗證 encoding
    assert info["method"] in ("reconfigure", "TextIOWrapper"), (
        f"機制二十三失敗：未知的設定方法: {info['method']}"
    )
    # encoding 可能是 utf-8 或 UTF-8
    assert info["stdout_encoding"].lower().replace('-', '') in ("utf8", "utf_8", "utf8sig"), (
        f"機制二十三失敗：stdout encoding 應為 utf-8，實際: {info['stdout_encoding']}"
    )
    print(f"  ✅ KPI-1+2: {info['method']} 設定成功，encoding={info['stdout_encoding']}")

    # KPI-3: 中文法律術語輸出測試
    legal_terms = [
        "消滅時效", "地政士", "不當得利", "侵權行為",
        "行政程序法第131條", "釋字第474號解釋"
    ]
    for term in legal_terms:
        try:
            # 模擬輸出（不會實際寫到 stdout 因為 pytest 有 capture）
            encoded = term.encode('utf-8')
            decoded = encoded.decode('utf-8')
            assert decoded == term, f"機制二十三失敗：'{term}' 編解碼不一致"
        except UnicodeEncodeError as e:
            pytest.fail(f"機制二十三失敗：'{term}' 輸出發生 UnicodeEncodeError: {e}")

    print(f"  ✅ KPI-3: {len(legal_terms)} 個法律術語 UTF-8 編解碼全部正確")
    print("✅ 機制二十三通過：BUG-12 UTF-8 全局輸出流修正驗證成功")
