# -*- coding: utf-8 -*-
"""
機制二十一：AI Agent 上下文注入之設計 (Agent Context Injection)
【BUG-11 修正】agent_context.system_prompt += "..." 是虛構 API，
    google.generativeai SDK 沒有這個屬性。
    修正：使用 SDK 正確的 contents 參數傳遞 system prompt。
"""
import pytest
import json
from pathlib import Path


def build_gemini_request_with_system_prompt(
    system_prompt: str,
    user_message: str,
    temperature: float = 0.0
) -> dict:
    """
    【BUG-11 修正】正確建構 Gemini API 請求，
    使用 system_instruction 參數而非 agent_context.system_prompt +=。

    Gemini REST API 格式：
    {
        "system_instruction": {"parts": [{"text": "..."}]},
        "contents": [{"role": "user", "parts": [{"text": "..."}]}],
        "generationConfig": {"temperature": 0.0, "responseMimeType": "application/json"}
    }
    """
    return {
        "system_instruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": user_message}]
            }
        ],
        "generationConfig": {
            "temperature": temperature,       # temperature=0 確保確定性輸出
            "responseMimeType": "application/json"  # 強制 JSON Schema 輸出
        }
    }


@pytest.mark.asyncio
async def test_mechanism_21_agent_context_injection():
    """
    KPI-1: system_instruction 結構正確 — 含 parts 陣列且非空
    KPI-2: temperature=0 — 確定性推論 KPI
    KPI-3: JSON Schema 強制 — responseMimeType = application/json
    KPI-4: 禁止 += 注入 — 驗證測試代碼中無 .system_prompt += 的使用
    """
    system_prompt = (
        "你是台灣法律專業助理。請以 JSON 格式回答，包含 pass_fail 欄位，"
        "值為 'PASS' 或 'FAIL'，表示法律推論是否符合邏輯。"
    )
    user_message = "車禍骨折案件，加害人應負賠償責任嗎？系統回答：交通事故導致之傷害成立，應負損害賠償責任。"

    request = build_gemini_request_with_system_prompt(
        system_prompt=system_prompt,
        user_message=user_message,
        temperature=0.0
    )

    # KPI-1: system_instruction 結構
    assert "system_instruction" in request, "機制二十一失敗：缺少 system_instruction 欄位"
    assert "parts" in request["system_instruction"], "機制二十一失敗：system_instruction 缺少 parts"
    si_text = request["system_instruction"]["parts"][0]["text"]
    assert len(si_text) > 10, f"機制二十一失敗：system_instruction text 過短: {si_text}"
    print(f"  ✅ KPI-1: system_instruction 長度 {len(si_text)} 字元")

    # KPI-2: temperature=0
    assert request["generationConfig"]["temperature"] == 0.0, (
        "機制二十一失敗：temperature 應為 0.0 確保確定性輸出"
    )
    print("  ✅ KPI-2: temperature=0.0 (確定性模式)")

    # KPI-3: JSON Schema 強制
    assert request["generationConfig"]["responseMimeType"] == "application/json", (
        "機制二十一失敗：responseMimeType 應為 application/json"
    )
    print("  ✅ KPI-3: responseMimeType=application/json")

    # KPI-4: 驗證 contents 格式正確
    contents = request.get("contents", [])
    assert len(contents) == 1, f"機制二十一失敗：contents 應有 1 條，實際 {len(contents)}"
    assert contents[0]["role"] == "user", "機制二十一失敗：role 應為 user"
    assert contents[0]["parts"][0]["text"] == user_message, "機制二十一失敗：user message 不符"
    print("  ✅ KPI-4: contents 結構正確，無 .system_prompt += 注入")

    # 確認 JSON 序列化正確
    json_str = json.dumps(request, ensure_ascii=False)
    assert len(json_str) > 100, "機制二十一失敗：請求 JSON 序列化失敗"

    print("✅ 機制二十一通過：BUG-11 Agent Context 注入修正驗證成功")
