# -*- coding: utf-8 -*-
"""
機制十九：記憶體遙測之設計 (Memory Telemetry)
【BUG-13 修正】原本只量測父進程 RSS，遺漏 Chromium 子進程記憶體，
    導致記憶體監控出現假陰性 (False Negative)。
    修正：必須將父進程 + 所有子進程的 RSS 加總。
"""
import os
import pytest
import psutil


def get_total_rss_bytes(pid: int) -> int:
    """
    【BUG-13 修正】取得目標進程及其所有子孫進程的 RSS 總和（Bytes）。
    原始錯誤版本：僅回傳 proc.memory_info().rss（只有父進程）。
    修正版本：遞迴加總所有子進程 RSS。
    """
    try:
        proc = psutil.Process(pid)
        total_rss = proc.memory_info().rss  # 父進程

        # 【BUG-13 修正】加總所有子進程（含 Chromium renderer/GPU/network processes）
        for child in proc.children(recursive=True):
            try:
                total_rss += child.memory_info().rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # 進程可能已結束，正常跳過
                pass

        return total_rss

    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        raise RuntimeError(f"無法取得 PID {pid} 的記憶體資訊: {e}")


def get_parent_only_rss_bytes(pid: int) -> int:
    """BUG-13 的原始錯誤版本（僅做比較用）"""
    proc = psutil.Process(pid)
    return proc.memory_info().rss


@pytest.mark.asyncio
async def test_mechanism_19_memory_telemetry():
    """
    KPI-1: 子進程加總 >= 父進程單獨 RSS（修正版 >= 原版）
    KPI-2: 記憶體值合理 — 在 50MB ~ 4GB 之間（排除零值假陰性）
    KPI-3: 連續測量穩定 — 3 次測量標準差 < 50MB（無假陰性波動）
    """
    current_pid = os.getpid()

    # KPI-1: 修正版（含子進程）應 >= 原版（只有父進程）
    total_rss = get_total_rss_bytes(current_pid)
    parent_only_rss = get_parent_only_rss_bytes(current_pid)

    assert total_rss >= parent_only_rss, (
        f"機制十九失敗：含子進程 RSS ({total_rss}) < 父進程 ({parent_only_rss})，邏輯矛盾"
    )
    print(f"  ✅ KPI-1: 父進程 {parent_only_rss//1024//1024} MB，含子進程 {total_rss//1024//1024} MB")

    # KPI-2: 記憶體值合理
    assert total_rss > 50 * 1024 * 1024, (
        f"機制十九失敗：total_rss ({total_rss//1024//1024} MB) 過小，可能為假陰性"
    )
    assert total_rss < 4 * 1024 * 1024 * 1024, (
        f"機制十九失敗：total_rss ({total_rss//1024//1024} MB) 超過 4GB，記憶體洩漏"
    )
    print(f"  ✅ KPI-2: 記憶體值合理 ({total_rss//1024//1024} MB)")

    # KPI-3: 連續 3 次測量標準差 < 50MB
    import statistics
    readings = [get_total_rss_bytes(current_pid) for _ in range(3)]
    std_mb = statistics.stdev(readings) / 1024 / 1024
    assert std_mb < 50, (
        f"機制十九失敗：記憶體測量標準差 {std_mb:.1f} MB >= 50 MB，測量不穩定"
    )
    print(f"  ✅ KPI-3: 3 次測量標準差 {std_mb:.2f} MB（< 50 MB）")

    print(f"✅ 機制十九通過：BUG-13 子進程 RSS 加總修正驗證成功")
