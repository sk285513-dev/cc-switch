# -*- coding: utf-8 -*-
"""
機制二十二：截圖命名與狀態索引之設計 (Screenshot Naming & State Indexing)
確保截圖命名帶有 state_id 前綴，建立視覺測試的可追蹤索引。
"""
import pytest
import re
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright


def generate_screenshot_filename(state_id: int, feature_tag: str = "") -> str:
    """
    論文中規定的截圖命名規範：State_{state_id:03d}_{feature_tag}.png
    確保按 state_id 字典序排序後對應真值表。
    """
    if feature_tag:
        safe_tag = re.sub(r'[^\w\u4e00-\u9fff]', '_', feature_tag)
        return f"State_{state_id:03d}_{safe_tag}.png"
    return f"State_{state_id:03d}.png"


@pytest.mark.asyncio
async def test_mechanism_22_screenshot_naming(tmp_path: Path):
    """
    KPI-1: 命名規範符合 — State_NNN.png 格式
    KPI-2: state_id 零填充 — 3 位數零填充保證正確排序
    KPI-3: 截圖實體落地 — 檔案實際寫入磁碟
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # 模擬法律系統頁面狀態
        test_states = [
            (1, "憲法查詢"),
            (2, "民法搜尋"),
            (10, "刑法分析"),
            (100, "行政法"),
        ]

        screenshot_dir = tmp_path / "screenshots"
        screenshot_dir.mkdir(parents=True)

        await page.set_content("""
        <html><body>
          <div class="stApp"><h1>法律系統測試介面</h1></div>
        </body></html>
        """)

        created_files = []
        for state_id, feature in test_states:
            filename = generate_screenshot_filename(state_id, feature)
            file_path = screenshot_dir / filename
            await page.screenshot(path=str(file_path))
            created_files.append((filename, file_path))

        await browser.close()

    # KPI-1: 命名規範驗證
    pattern = re.compile(r'^State_\d{3}.*\.png$')
    for filename, file_path in created_files:
        assert pattern.match(filename), (
            f"機制二十二失敗：'{filename}' 不符合 State_NNN.png 命名規範"
        )

    # KPI-2: 零填充驗證
    assert "State_001_" in created_files[0][0], f"機制二十二失敗：state_id=1 應為 001，實際：{created_files[0][0]}"
    assert "State_010_" in created_files[2][0], f"機制二十二失敗：state_id=10 應為 010，實際：{created_files[2][0]}"
    assert "State_100_" in created_files[3][0], f"機制二十二失敗：state_id=100 應為 100，實際：{created_files[3][0]}"
    print("  ✅ KPI-2: 三位數零填充正確（001, 010, 100）")

    # KPI-3: 實體落地
    for filename, file_path in created_files:
        assert file_path.exists(), f"機制二十二失敗：截圖 {filename} 未落地"
        assert file_path.stat().st_size > 100, f"機制二十二失敗：截圖 {filename} 大小異常（< 100 bytes）"

    print(f"  ✅ KPI-3: {len(created_files)} 張截圖全部落地，最小 {min(f.stat().st_size for _, f in created_files)} bytes")
    print("✅ 機制二十二通過：截圖命名與狀態索引驗證成功")
