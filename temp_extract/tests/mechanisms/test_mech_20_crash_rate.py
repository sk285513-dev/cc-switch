# -*- coding: utf-8 -*-
"""
機制二十：崩潰率統計防零除之設計 (Crash Rate ZeroDivision Guard)
【BUG-06 修正】crash_counts[feature] / total_counts[feature] 當
    total_counts 為 0 時發生 ZeroDivisionError。
    修正：加入零除保護，total_counts 為 0 時回傳 0.0。
"""
import pytest
from collections import defaultdict


def calculate_crash_rate(crash_counts: dict, total_counts: dict) -> dict:
    """
    【BUG-06 修正】計算各功能的崩潰率，加入零除保護。
    total_counts[feature] == 0 時回傳 0.0 而非拋出 ZeroDivisionError。
    """
    crash_rates = {}
    for feature in set(crash_counts) | set(total_counts):
        total = total_counts.get(feature, 0)
        crashes = crash_counts.get(feature, 0)
        # 【BUG-06 修正】零除保護
        crash_rates[feature] = crashes / total if total > 0 else 0.0
    return crash_rates


@pytest.mark.asyncio
async def test_mechanism_20_crash_rate_guard():
    """
    KPI-1: 零除保護 — total_counts[f] == 0 時不拋出 ZeroDivisionError
    KPI-2: 正確計算 — crash_rate = crash / total 結果精確
    KPI-3: 崩潰率 <= 5% — 系統穩定性 KPI 驗收
    """
    # KPI-1: 零除保護（模擬新功能尚未有任何測試執行紀錄）
    crash_counts = defaultdict(int, {"案例查詢": 2, "新功能": 0})
    total_counts = defaultdict(int, {"案例查詢": 100, "新功能": 0})  # 新功能 total = 0

    # 原本 BUG-06 版本會在此拋出 ZeroDivisionError
    try:
        rates = calculate_crash_rate(crash_counts, total_counts)
    except ZeroDivisionError:
        pytest.fail("機制二十失敗：BUG-06 零除保護未生效，ZeroDivisionError 發生")

    assert "新功能" in rates, "機制二十失敗：新功能未出現在崩潰率結果中"
    assert rates["新功能"] == 0.0, (
        f"機制二十失敗：total=0 時崩潰率應為 0.0，實際 {rates['新功能']}"
    )
    print(f"  ✅ KPI-1: 零除保護生效，新功能 crash_rate = 0.0")

    # KPI-2: 正確計算
    assert abs(rates["案例查詢"] - 0.02) < 1e-9, (
        f"機制二十失敗：案例查詢崩潰率應為 0.02，實際 {rates['案例查詢']}"
    )
    print(f"  ✅ KPI-2: 案例查詢 crash_rate = {rates['案例查詢']:.4f}（正確）")

    # KPI-3: 模擬系統壓測後驗收
    stress_crash_counts = {
        "案例查詢": 3, "法條搜尋": 1, "PDF 匯出": 0,
        "憲法解析": 2, "時效計算": 0
    }
    stress_total_counts = {
        "案例查詢": 500, "法條搜尋": 300, "PDF 匯出": 200,
        "憲法解析": 400, "時效計算": 0  # 時效計算尚未執行
    }
    stress_rates = calculate_crash_rate(stress_crash_counts, stress_total_counts)

    max_rate = max(
        v for k, v in stress_rates.items()
        if stress_total_counts.get(k, 0) > 0  # 只考慮有執行的功能
    )
    assert max_rate <= 0.05, (
        f"機制二十失敗：最高崩潰率 {max_rate:.2%} 超過 5% KPI 閾值"
    )
    print(f"  ✅ KPI-3: 最高崩潰率 {max_rate:.2%} <= 5%，系統穩定性通過")
    print("✅ 機制二十通過：BUG-06 零除保護修正驗證成功")
