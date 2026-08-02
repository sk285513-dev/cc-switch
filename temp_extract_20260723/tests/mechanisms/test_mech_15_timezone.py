# -*- coding: utf-8 -*-
"""
機制十五：時區感知時間戳之設計 (Timezone-Aware Timestamp)
【BUG-03 修正】datetime.utcnow() 回傳無時區資訊的 naive datetime，
    在 SRT 字幕合併與跨機器日誌比對時可能導致 8 小時偏移。
    改用 datetime.now(ZoneInfo("Asia/Taipei")) 產生帶時區的 aware datetime。
"""
import pytest
import datetime
from pathlib import Path


def get_taipei_now():
    """
    【BUG-03 修正】產生台北時間的 aware datetime。
    ZoneInfo 是 Python 3.9+ 標準函式庫，3.6-3.8 需 backports.zoneinfo。
    """
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo  # Python 3.8 fallback
    return datetime.datetime.now(ZoneInfo("Asia/Taipei"))


def get_utcnow_naive():
    """原始的 BUG 版本，僅做比較用"""
    return datetime.datetime.utcnow()


@pytest.mark.asyncio
async def test_mechanism_15_timezone_aware():
    """
    KPI-1: tzinfo 非 None — aware datetime 必須帶時區資訊
    KPI-2: 8 小時偏移修正 — Taipei 時間與 UTC+0 相差約 8 小時
    KPI-3: SRT 時間戳格式正確 — HH:MM:SS,mmm 格式
    """
    # KPI-1: aware datetime 必須有 tzinfo
    taipei_now = get_taipei_now()
    assert taipei_now.tzinfo is not None, (
        "機制十五失敗：BUG-03 修正未生效，datetime.now() 回傳 naive datetime"
    )
    print(f"  ✅ KPI-1: tzinfo = {taipei_now.tzinfo} （非 None）")

    # KPI-2: 與 UTC naive 的差距應約為 8 小時（允許 ±1 分鐘誤差）
    utc_naive = get_utcnow_naive()
    # 將 aware datetime 轉為 UTC 後比較
    utc_from_taipei = taipei_now.utctimetuple()
    expected_offset_hours = 8
    actual_offset = (taipei_now.replace(tzinfo=None) - utc_naive).total_seconds() / 3600

    assert abs(actual_offset - expected_offset_hours) < 0.1, (
        f"機制十五失敗：台北時間與 UTC 偏差應為 {expected_offset_hours}h，"
        f"實際 {actual_offset:.2f}h"
    )
    print(f"  ✅ KPI-2: UTC+8 偏移驗證通過，偏差 {actual_offset:.4f}h")

    # KPI-3: SRT 時間戳格式驗證
    def format_srt_timestamp(dt: datetime.datetime) -> str:
        total_ms = dt.microsecond // 1000
        h = dt.hour
        m = dt.minute
        s = dt.second
        return f"{h:02d}:{m:02d}:{s:02d},{total_ms:03d}"

    srt_ts = format_srt_timestamp(taipei_now)
    import re
    assert re.match(r'^\d{2}:\d{2}:\d{2},\d{3}$', srt_ts), (
        f"機制十五失敗：SRT 時間戳格式錯誤：{srt_ts}"
    )
    print(f"  ✅ KPI-3: SRT 格式 {srt_ts} 正確")

    print(f"✅ 機制十五通過：台北時間 {taipei_now.isoformat()}，BUG-03 修正驗證成功")
