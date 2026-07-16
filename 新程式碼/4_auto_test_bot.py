# -*- coding: utf-8 -*-
import os
import sys
import json
import time
import wave
import struct
import subprocess
import shutil
import requests

# 將 scripts 目錄加入 PATH
sys.path.append(os.path.join(os.path.dirname(__file__), "scripts"))

from case_manager import load_cases, save_cases
from multimodal_input import MultimodalLegalInput
from agent_core_pro import LocalLegalAgent

def print_header(title):
    print("=" * 60)
    print(f" [Bot Task] {title}")
    print("=" * 60)

def print_success(msg):
    print(f"  [OK] {msg}")

def print_failure(msg):
    print(f"  [FAIL] {msg}")

# 保存原始 requests.post，供 Mock 恢復使用
ORIGINAL_POST = requests.post

class MockChaosResponse:
    def __init__(self, status_code, json_data=None, text_data=None):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text_data or ""

    def json(self):
        if self._json_data is None:
            raise ValueError("No JSON content")
        return self._json_data

# ==========================================
# 1. 個案管理 (Case Manager) 邊界與極限測試
# ==========================================
def test_case_manager_extreme():
    print_header("1. 個案管理 (Case Manager) 邊界與極限壓力測試")
    
    # 測試點 1.1：特殊字元與 SQL/XSS 注入字串測試
    print("  -> 測試點 1.1：注入特殊字元與 SQL/XSS/控制碼...")
    cases = load_cases()
    test_id = "CASE-BOT-CHAOS-001"
    
    had_test_case = test_id in cases
    original_test_data = cases.get(test_id)
    
    # 惡意特殊字串注入
    special_comment = "單雙引號'\" 標籤<script>alert(1)</script> SQL注入' OR 1=1 -- 換行\n\r 控制碼\x00 表情符號🦁⚖️🇹🇼"
    cases[test_id] = {
        "title": "混沌注入個案",
        "current_stage": "極限測試",
        "stakeholders": ["駭客A", "測試員B"],
        "dialog_history": [],
        "documents_and_evidence": [
            {"id": "doc_stress", "name": "防護證物.pdf", "comment": special_comment}
        ],
        "precedents": [],
        "claims": []
    }
    
    # 寫入
    save_cases(cases)
    
    # 重新讀取驗證
    reloaded = load_cases()
    if test_id in reloaded:
        comment_read = reloaded[test_id]["documents_and_evidence"][0]["comment"]
        if comment_read == special_comment:
            print_success("特殊字元與 SQL/XSS 注入字元完整寫入且讀出一致！")
        else:
            print_failure(f"讀出字元不符！\n原本: {special_comment}\n讀出: {comment_read}")
    else:
        print_failure("寫入特殊字元後無法讀取該個案！")

    # 測試點 1.2：大數據壓力寫入測試 (10,000字巨型字串)
    print("  -> 測試點 1.2：寫入 10,000 字巨型評論字串...")
    large_comment = "⚖️" * 5000  # 10,000 bytes 以上的字元
    cases[test_id]["documents_and_evidence"][0]["comment"] = large_comment
    
    t0 = time.time()
    save_cases(cases)
    write_time = time.time() - t0
    
    reloaded_large = load_cases()
    large_comment_read = reloaded_large[test_id]["documents_and_evidence"][0]["comment"]
    if large_comment_read == large_comment:
        print_success(f"巨型資料寫入與讀出無誤，寫入花費時間: {write_time:.4f} 秒")
    else:
        print_failure("巨型資料讀出有損壞或丟失！")
        
    # 清理測試案
    if had_test_case:
        cases[test_id] = original_test_data
    else:
        cases.pop(test_id, None)
    save_cases(cases)
    print("  -> 已還原個案檔原始狀態")


# ==========================================
# 2. 多模態語音轉譯 (Whisper) 損壞與異常檔案測試
# ==========================================
def test_multimodal_audio_extreme():
    print_header("2. 多模態 Whisper 轉譯損壞與無效檔案測試")
    
    processor = MultimodalLegalInput(model_size="tiny")
    
    # 測試點 2.1：檔案完全不存在
    print("  -> 測試點 2.1：傳入非實體存在之音檔路徑...")
    fake_path = "C:/LocalAI_Workstation/Data/not_exist_file_999.wav"
    res_fake = processor.transcribe_audio(fake_path)
    print(f"     [回應結果] {res_fake}")
    if "失敗" in res_fake or "錯誤" in res_fake or "FileNotFoundError" in str(res_fake) or "not found" in str(res_fake).lower():
        print_success("非實體存在之檔案處理防錯驗證通過！")
    else:
        print_failure("傳入不存在檔案時未返回預期錯誤訊息！")

    # 測試點 2.2：0 位元組損壞檔案
    print("  -> 測試點 2.2：傳入 0 位元組之損壞音檔...")
    corrupted_wav = "C:/LocalAI_Workstation/Data/corrupted_zero.wav"
    try:
        with open(corrupted_wav, "wb") as f:
            pass  # 建立空的 0-byte 檔案
        
        res_corr = processor.transcribe_audio(corrupted_wav)
        print(f"     [回應結果] {res_corr}")
        if "失敗" in res_corr or "錯誤" in res_corr or "Exception" in str(res_corr) or len(res_corr) < 50:
            print_success("0位元組損壞檔案處理防錯驗證通過！")
        else:
            print_failure("0位元組檔案未正確引發轉譯失敗提示！")
    except Exception as e:
        print_failure(f"建立測試 0 檔案出錯: {e}")
    finally:
        if os.path.exists(corrupted_wav):
            os.remove(corrupted_wav)

    # 測試點 2.3：偽裝成音訊檔的純文字檔 (改副檔名欺騙)
    print("  -> 測試點 2.3：傳入純文字偽裝之 wav 檔案...")
    fake_wav = "C:/LocalAI_Workstation/Data/fake_text.wav"
    try:
        with open(fake_wav, "w", encoding="utf-8") as f:
            f.write("這是一行偽裝成語音檔的台灣法律裁判見解純文字，內容並非 PCM 音訊數據。")
            
        res_fake_wav = processor.transcribe_audio(fake_wav)
        print(f"     [回應結果] {res_fake_wav}")
        if "失敗" in res_fake_wav or "錯誤" in res_fake_wav or "Exception" in str(res_fake_wav):
            print_success("偽裝檔案解碼防錯驗證通過！")
        else:
            print_failure("非音訊檔案未正確引發解碼失敗！")
    except Exception as e:
        print_failure(f"建立測試偽裝檔案出錯: {e}")
    finally:
        if os.path.exists(fake_wav):
            os.remove(fake_wav)


# ==========================================
# 3. Ollama API 混沌注入測試 (Chaos Mocking)
# ==========================================
def test_ollama_api_chaos():
    print_header("3. Ollama API 混沌注入與防崩潰測試")
    
    agent = LocalLegalAgent()
    
    # 定義自訂的 Mock 攔截邏輯
    current_chaos_scenario = None
    
    def mock_post(url, *args, **kwargs):
        # 僅攔截 Ollama chat 相關 API
        if "/api/chat" in url:
            if current_chaos_scenario == "HTTP_500_NON_JSON":
                # 模擬伺服器內部錯誤，回傳 HTML 格式
                return MockChaosResponse(status_code=500, text_data="<html><body><h1>500 Internal Server Error</h1></body></html>")
                
            elif current_chaos_scenario == "EMPTY_JSON":
                # 模擬回傳空 JSON 物件
                return MockChaosResponse(status_code=200, json_data={})
                
            elif current_chaos_scenario == "MISSING_CONTENT":
                # 模擬回傳正確 JSON 但缺少重要 key
                return MockChaosResponse(status_code=200, json_data={"message": {"role": "assistant"}})
                
            elif current_chaos_scenario == "INVALID_TYPE":
                # 模擬 message content 是個整數而非字串
                return MockChaosResponse(status_code=200, json_data={"message": {"role": "assistant", "content": 12345}})
                
            elif current_chaos_scenario == "TIMEOUT":
                # 模擬逾時
                raise requests.exceptions.Timeout("Ollama API connection timed out.")
                
        # 其他 API (例如 embedding) 走正常呼叫，或是我們預設返回 dummy
        if "/api/embeddings" in url:
            return MockChaosResponse(status_code=200, json_data={"embedding": [0.0] * 768})
            
        return ORIGINAL_POST(url, *args, **kwargs)

    # 套用 Mock
    requests.post = mock_post
    
    scenarios = ["HTTP_500_NON_JSON", "EMPTY_JSON", "MISSING_CONTENT", "INVALID_TYPE", "TIMEOUT"]
    
    for scenario in scenarios:
        current_chaos_scenario = scenario
        print(f"  -> 測試情境: {scenario} 注入中...")
        try:
            # 呼叫 chat，若背後防錯邏輯完善，不論 API 回傳多糟糕都不會拋出未處理異常
            reply, evidence = agent.chat("測試混沌問題")
            print(f"     [回應長度] {len(str(reply))} 字 | 範例: {str(reply)[:35]}...")
            print_success(f"情境 {scenario} 防崩潰驗證通過！")
        except Exception as e:
            print_failure(f"在 {scenario} 情境下，系統拋出未捕獲的異常崩潰：{e}")
            import traceback
            traceback.print_exc()

    # 恢復原始的 requests.post
    requests.post = ORIGINAL_POST
    print("  -> 已還原原始 requests.post API 套件設定")


# ==========================================
# 4. ChromaDB 向量檢索邊界測試
# ==========================================
def test_chromadb_edge_cases():
    print_header("4. ChromaDB 向量檢索邊界與異常輸入測試")
    
    agent = LocalLegalAgent()
    
    # 測試點 4.1：空字串檢索
    print("  -> 測試點 4.1：傳入空字串或純空白進行 Hybrid 檢索...")
    try:
        results = agent.search_hybrid("")
        print(f"     [結果數量] {len(results)}")
        print_success("空字串檢索安全處理通過！")
    except Exception as e:
        print_failure(f"空字串檢索時崩潰: {e}")

    # 測試點 4.2：超長字串檢索
    print("  -> 測試點 4.2：傳入 10,000 字超長 query 進行檢索...")
    super_long_query = "民法第一百八十四條侵權行為責任。" * 300
    try:
        results = agent.search_hybrid(super_long_query)
        print(f"     [結果數量] {len(results)}")
        print_success("超長字串檢索安全處理與向量化防爆通過！")
    except Exception as e:
        print_failure(f"超長字串檢索時崩潰: {e}")


if __name__ == "__main__":
    # 強制將輸出設為 UTF-8 相容模式，防止 cp950 錯誤
    if sys.stdout.encoding != 'utf-8':
        try:
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        except:
            pass

    print("============================================================")
    print("      LexMind-Omni v1.5 極限與混沌混沌工程測試套件 (Chaos Bot)")
    print("============================================================")
    
    test_case_manager_extreme()
    test_multimodal_audio_extreme()
    test_ollama_api_chaos()
    test_chromadb_edge_cases()
    
    print("============================================================")
    print("                 極限與混沌測試執行完畢！")
    print("============================================================")
