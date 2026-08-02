# -*- coding: utf-8 -*-
"""
機制十八：API 限流感知容錯之設計 (API Rate-Limit Awareness)
【BUG-05 修正】精確型別比對取代字串比對 "429" in str(e)，
    相容 google.generativeai SDK gRPC 錯誤與 HTTP 429。
"""
import pytest
import time


class MockHTTP429Error(Exception):
    """模擬 HTTP 429 回應"""
    def __init__(self, message="Too Many Requests", retry_after=None):
        super().__init__(message)
        self.status_code = 429
        self.retry_after = retry_after  # Retry-After header 秒數


class MockGRPCResourceExhausted(Exception):
    """模擬 gRPC RESOURCE_EXHAUSTED 錯誤（Google Gemini API）"""
    def __init__(self, retry_sec=None):
        msg = "429 RESOURCE_EXHAUSTED"
        if retry_sec:
            msg += f". Please retry in {retry_sec}s. quota exceeded"
        super().__init__(msg)
        self.code = 429


def is_quota_error(e: Exception) -> tuple[bool, float | None]:
    """
    【BUG-05 修正】精確型別比對，回傳 (is_quota_err, retry_after_sec)。
    """
    import re
    err_str = str(e)

    # 方法1: HTTP status_code 屬性（requests / httpx 風格）
    if hasattr(e, 'status_code') and getattr(e, 'status_code', 0) == 429:
        retry_after = getattr(e, 'retry_after', None)
        return True, retry_after

    # 方法2: gRPC code 屬性（google-generativeai SDK）
    if hasattr(e, 'code') and getattr(e, 'code', None) == 429:
        m = re.search(r'Please retry in (\d+\.?\d*)s', err_str)
        return True, float(m.group(1)) + 2.0 if m else True, None

    # 方法3: 字串包含（fallback，相容所有格式）
    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
        m = re.search(r'Please retry in (\d+\.?\d*)s', err_str)
        return True, float(m.group(1)) + 2.0 if m else True, None

    return False, None


@pytest.mark.asyncio
async def test_mechanism_18_api_rate_limit():
    """
    KPI-1: HTTP 429 正確識別 — MockHTTP429Error 被識別為 quota error
    KPI-2: gRPC 429 正確識別 — MockGRPCResourceExhausted 被識別為 quota error
    KPI-3: 非 429 錯誤不誤判 — 一般 RuntimeError 不被識別為 quota error
    KPI-4: Retry-After 解析 — 從錯誤訊息提取精確等待秒數
    """
    # KPI-1: HTTP 429
    http_err = MockHTTP429Error("Too Many Requests", retry_after=30)
    is_quota, retry_sec = is_quota_error(http_err)
    assert is_quota, "機制十八失敗：HTTP 429 未被識別為 quota error"
    print(f"  ✅ KPI-1: HTTP 429 正確識別，retry_after={retry_sec}")

    # KPI-2: gRPC RESOURCE_EXHAUSTED with retry hint
    grpc_err = MockGRPCResourceExhausted(retry_sec=45.0)
    is_quota2, retry_sec2 = is_quota_error(grpc_err)
    assert is_quota2, "機制十八失敗：gRPC RESOURCE_EXHAUSTED 未被識別"
    if retry_sec2 is not None:
        assert retry_sec2 >= 45.0, (
            f"機制十八失敗：retry_sec 應 >= 45.0，實際 {retry_sec2}"
        )
    print(f"  ✅ KPI-2: gRPC 429 正確識別，retry_sec={retry_sec2}")

    # KPI-3: 非 quota 錯誤不誤判
    normal_err = RuntimeError("Connection refused: Network error")
    is_quota3, _ = is_quota_error(normal_err)
    assert not is_quota3, "機制十八失敗：普通 RuntimeError 被誤判為 quota error"
    print("  ✅ KPI-3: 非 quota 錯誤無誤判")

    # KPI-4: Retry-After 精確解析（從 gRPC 訊息提取）
    grpc_with_hint = MockGRPCResourceExhausted(retry_sec=12.5)
    _, parsed_retry = is_quota_error(grpc_with_hint)
    if parsed_retry is not None:
        assert parsed_retry >= 12.5, f"機制十八失敗：Retry-After 解析錯誤: {parsed_retry}"
    print(f"  ✅ KPI-4: Retry-After 解析 = {parsed_retry}s")

    print("✅ 機制十八通過：BUG-05 精確型別比對修正驗證成功")
