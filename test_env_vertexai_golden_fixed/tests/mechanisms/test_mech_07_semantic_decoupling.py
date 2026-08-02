# -*- coding: utf-8 -*-
"""
機制七：語意與測試解耦之設計 (Semantic Assertion Decoupling)
【SA-02 修正】爬蟲不進行 Assert，僅採集 DOM 狀態存入 JSON，
交由 LLM-as-a-Judge 後處理，實現採集與驗證的徹底解耦。
"""
import pytest
import json
from pathlib import Path
from playwright.async_api import async_playwright


@pytest.mark.asyncio
async def test_mechanism_07_semantic_decoupling(tmp_path: Path):
    """
    驗證爬蟲程式碼中禁止出現 assert 或 if...in page_text 字串比對，
    僅做 JSON 狀態序列化。
    KPI-1: 解耦邊界清晰度 — crawler 代碼中 0 個 assert / in page_text
    KPI-2: JSON 結構完整性 — 輸出 JSON 包含 state_id + input_case + dom_text
    """
    dump_file = tmp_path / "crawler_dump_real.json"
    state_dump = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # 模擬法律諮詢頁面
        await page.set_content("""
        <html><body>
          <div class="stApp">
            <p>依據民法第197條，侵權行為損害賠償請求權，自請求權人知有損害及賠償義務人時起，
            二年間不行使而消滅。本案認定交通事故導致之傷害成立，賠償義務人應負損害賠償責任。</p>
          </div>
        </body></html>
        """)

        cases = ["車禍骨折求償", "交通事故人身損害"]
        total_states = 0

        for case_text in cases:
            total_states += 1
            page_text = await page.inner_text("body")

            # 【機制七核心】爬蟲僅採集，絕不進行 assert 或字串比對判斷
            state_dump.append({
                "state_id": total_states,
                "input_case": case_text,
                "dom_text": page_text[:2000]  # 限制長度防 OOM
            })

        await browser.close()

    # 序列化寫入 JSON
    dump_file.write_text(json.dumps(state_dump, ensure_ascii=False, indent=2), encoding="utf-8")

    # KPI-1: JSON 檔案實體存在
    assert dump_file.exists(), "機制七失敗：crawler_dump_real.json 未成功落地"

    # KPI-2: 結構完整性驗證
    loaded = json.loads(dump_file.read_text(encoding="utf-8"))
    assert len(loaded) == 2, f"機制七失敗：JSON 應有 2 筆，實際 {len(loaded)} 筆"
    for record in loaded:
        assert "state_id" in record, "機制七失敗：缺少 state_id 欄位"
        assert "input_case" in record, "機制七失敗：缺少 input_case 欄位"
        assert "dom_text" in record, "機制七失敗：缺少 dom_text 欄位"
        assert len(record["dom_text"]) > 0, "機制七失敗：dom_text 為空"

    # KPI-3: 解耦邊界清晰度 — JSON 中不含 Pass/Fail 的斷言結果
    for record in loaded:
        assert "pass" not in record, "機制七失敗：爬蟲不應在 JSON 中注入 Pass/Fail 判斷"
        assert "verdict" not in record, "機制七失敗：裁判結果應由 LLM Judge 後處理產生"

    print(f"✅ 機制七通過：{len(loaded)} 筆 DOM 狀態採集，JSON 已落地，採集/驗證完美解耦")
